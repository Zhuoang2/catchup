"""Single-instance digest lifecycle, with database writes on the runner thread."""

import logging
import threading
from contextlib import closing
from datetime import timedelta

from cryptography.fernet import InvalidToken
from fastapi import FastAPI
from sqlalchemy import func, select

from catchup.collection import check_source
from catchup.crypto import decrypt_key
from catchup.digest.group import GroupItem, group_items
from catchup.digest.summarize import SummaryInput, SummaryResult, summarize_items
from catchup.llm.prompts import SUMMARY_MAX_TOKENS
from catchup.errors import AppError
from catchup.llm.client import AuthFailed, InsufficientBalance, ModelError
from catchup.models import (
    AppSettings, Digest, DigestItem, DigestRun, DigestTopic, Item, ModelConfig,
    Source, SourceCheck, utc_now,
)
from catchup.net.host_spacing import HostSpacer
from catchup.net.rate_limit import is_rate_limited
from catchup.transcripts.context import TranscriptContext
from catchup.sources.feeds import is_short
from catchup.transcripts.youtube import fetch_captions

ACTIVE = ("queued", "collecting", "summarizing", "grouping")
_start_lock = threading.Lock()
logger = logging.getLogger(__name__)
CREATOR_REASONS = {"captions_off", "no_captions", "blocked", "captions_failed", "no_transcript"}


def select_pending(rows, now, transcript_wait_days: int, caption_wait_hours: int):
    """Classify pending items without mutating expiry statuses before the save."""
    summaries = []
    updates: list[tuple[int, str]] = []
    waiting = deferred = 0
    for item, source in rows:
        status = item.transcript_status
        if status in ("found", "text") or (status is None and source.kind == "feed"):
            summaries.append((item, source.title))
        elif status in CREATOR_REASONS:
            updates.append((item.id, status))
        elif source.kind == "podcast" and status in (None, "to_fetch", "waiting"):
            if item.discovered_at + timedelta(days=transcript_wait_days) <= now:
                updates.append((item.id, "no_transcript"))
            else:
                waiting += 1
        elif status in ("caption_wait", "unplayable_wait"):
            if item.discovered_at + timedelta(hours=caption_wait_hours) <= now:
                updates.append((item.id, "no_captions" if status == "caption_wait" else "captions_failed"))
            else:
                waiting += 1
        elif status in (None, "to_fetch") and source.kind == "youtube":
            deferred += 1
    return summaries, updates, waiting, deferred


def caption_pass(factory, context: TranscriptContext) -> None:
    """Resolve YouTube items in recording order, committing every attempted item."""
    now = utc_now()
    with factory() as session:
        items = session.scalars(
            select(Item).join(Source, Item.source_id == Source.id)
            .where(Source.kind == "youtube", Item.state == "pending")
            .where(Item.transcript_status.in_((
                "to_fetch", "caption_wait", "unplayable_wait", "captions_off",
            )) | Item.transcript_status.is_(None))
            .order_by(Item.discovered_at, Item.id)
        ).all()
        for item in items:
            if context.youtube_skip_shorts and item.transcript_status in (None, "to_fetch") and is_short(item.link):
                item.state = "baseline"
                session.commit()
                continue
            if item.transcript_status in ("caption_wait", "unplayable_wait") and (
                item.discovered_at + timedelta(hours=context.settings.caption_wait_hours) <= now
            ):
                continue
            if not context.youtube_captions:
                item.transcript_status = "captions_off"
            elif context.captions_blocked or context.captions_remaining == 0:
                if item.transcript_status not in ("caption_wait", "unplayable_wait"):
                    item.transcript_status = "to_fetch"
            else:
                context.captions_remaining -= 1
                video_id = (item.identity_key.removeprefix("yt:video:")
                            if item.identity_key.startswith("yt:video:") else "")
                if video_id:
                    try:
                        status, text = fetch_captions(video_id, context.spacer)
                    except Exception as exc:
                        logger.warning("Caption fetch failed for item %s (%s)", item.id, type(exc).__name__)
                        status, text = "captions_failed", None
                else:
                    status, text = "captions_failed", None
                item.transcript_status = status
                if status == "blocked":
                    context.captions_blocked = True
                if status == "found" and text:
                    item.content_text = text
                    item.content_origin = "transcript"
                    item.summary = None
                    item.summary_language = None
            session.commit()


def active_run(session) -> DigestRun | None:
    return session.scalar(select(DigestRun).where(DigestRun.status.in_(ACTIVE)).order_by(DigestRun.id).limit(1))


def recover_runs(factory) -> None:
    with factory() as session:
        for run in session.scalars(select(DigestRun).where(DigestRun.status.in_(ACTIVE))):
            run.status = "failed"
            run.error_kind = "interrupted"
            run.error_message = "The run was interrupted. Generate again to retry pending items."
            run.finished_at = utc_now()
        session.commit()


def start_run(app: FastAPI, *, background: bool = True) -> DigestRun:
    with _start_lock, app.state.session_factory() as session:
        current = active_run(session)
        if current:
            raise AppError("run_active", "A digest run is already active.", 409, active_run_id=current.id)
        if session.get(ModelConfig, 1) is None:
            raise AppError("model_not_configured", "Set up a model in Settings before generating.", 409)
        run = DigestRun(status="queued", started_at=utc_now())
        session.add(run)
        session.commit()
        if background:
            threading.Thread(target=run_digest, args=(app, run.id), daemon=True).start()
        return run


def _stage(factory, run_id: int, status: str, *, total: int | None = None) -> None:
    with factory() as session:
        run = session.get(DigestRun, run_id)
        run.status = status
        if total is not None:
            run.items_total = total
        session.commit()


def _write_usage(run: DigestRun, usage: tuple[int, int] | None) -> None:
    if usage is not None:
        run.prompt_tokens, run.completion_tokens = usage


def _fail(factory, run_id: int, kind: str, message: str,
          usage: tuple[int, int] | None = None) -> None:
    with factory() as session:
        run = session.get(DigestRun, run_id)
        run.status = "failed"
        run.error_kind = kind
        run.error_message = message
        run.finished_at = utc_now()
        _write_usage(run, usage)
        session.commit()


def run_digest(app: FastAPI, run_id: int) -> None:
    """Synchronous entry point for tests; production calls it from a daemon thread."""
    factory = app.state.session_factory
    usage: tuple[int, int] | None = None
    try:
        with factory() as session:
            config = session.get(ModelConfig, 1)
            if config is None:
                raise AppError("model_not_configured", "Set up a model in Settings before generating.")
            language_row = session.get(AppSettings, 1)
            language = language_row.digest_language if language_row else "en"
            captions_enabled = language_row.youtube_captions if language_row else False
            skip_shorts = language_row.youtube_skip_shorts if language_row else True
            # Configuration and language are read once, before any source check.
            base_url, model_id = config.base_url, config.model_id
            key = decrypt_key(config.api_key_encrypted, app.state.settings.secret_key)
            source_ids = session.scalars(select(Source.id).order_by(Source.id)).all()
            context_window = config.context_window
        if context_window is None:
            try:
                with closing(app.state.model_client_factory(base_url, key, model_id)) as provider:
                    match = next((entry for entry in provider.list_models() if entry.id == model_id), None)
                value = match.context_window if match else None
                if type(value) is int and value > 0:
                    context_window = value
                    with factory() as session:
                        row = session.get(ModelConfig, 1)
                        if row and row.base_url == base_url and row.model_id == model_id:
                            row.context_window = value
                            session.commit()
            except Exception as exc:
                logger.warning("Model context window unavailable for run %s (%s)", run_id, type(exc).__name__)
        _stage(factory, run_id, "collecting")
        spacer = HostSpacer()
        transcripts = TranscriptContext(
            spacer=spacer, settings=app.state.settings, youtube_captions=captions_enabled,
            youtube_skip_shorts=skip_shorts, captions_remaining=app.state.settings.captions_per_run,
        )
        for source_id in source_ids:
            with factory() as session:
                source = session.get(Source, source_id)
                if source is not None:
                    check_source(session, source, run_id, app.state.settings,
                                 spacer=spacer, transcripts=transcripts)
        caption_pass(factory, transcripts)

        with factory() as session:
            rows = session.execute(
                select(Item, Source).join(Source, Item.source_id == Source.id)
                .where(Item.state == "pending").order_by(Item.id)
            ).all()
            ready, creator_updates, waiting, deferred = select_pending(
                rows, utc_now(), app.state.settings.transcript_wait_days,
                app.state.settings.caption_wait_hours,
            )
            inputs = [
                SummaryInput(item.id, item.title, item.content_text, item.summary,
                             item.summary_language, item.content_origin)
                for item, _ in ready
            ]
            names = {item.id: name for item, name in ready}
            run = session.get(DigestRun, run_id)
            run.waiting_count = waiting
            run.deferred_count = deferred
            session.commit()
        if not inputs and not creator_updates:
            with factory() as session:
                run = session.get(DigestRun, run_id)
                run.status = "no_new_content"
                run.finished_at = utc_now()
                session.commit()
            return

        _stage(factory, run_id, "summarizing", total=len(inputs))
        summaries: dict[int, SummaryResult] = {}

        def record(result: SummaryResult) -> None:
            # Called only on this runner thread. No SQLAlchemy session enters the pool.
            with factory() as session:
                if not result.unavailable:
                    item = session.get(Item, result.id)
                    if item is not None:
                        item.summary = result.summary
                        item.summary_language = language
                run = session.get(DigestRun, run_id)
                run.items_done += 1
                session.commit()
            summaries[result.id] = result

        topics = []
        if inputs:
            call_budget = (app.state.settings.single_call_chars
                           or (max(2_000, context_window - SUMMARY_MAX_TOKENS - 2_000)
                               if context_window else 60_000))
            with closing(app.state.model_client_factory(base_url, key, model_id)) as client:
                try:
                    summarize_items(client, inputs, language, call_budget, record,
                                    long_item_chars=app.state.settings.long_item_chars)
                    _stage(factory, run_id, "grouping")
                    with factory() as session:
                        group_inputs = [
                            GroupItem(item.id, item.title, names[item.id], summaries[item.id].summary)
                            for item in session.scalars(
                                select(Item).where(Item.id.in_([entry.id for entry in inputs])).order_by(Item.id)
                            )
                        ]
                    topics = group_items(client, group_inputs, language, app.state.settings.grouping_batch_chars)
                finally:
                    usage = getattr(client, "usage_totals", lambda: None)()

        # Snapshot and delivery share one transaction: a failed save cannot lose pending items.
        with factory() as session:
            items = {
                item.id: (item, source_name)
                for item, source_name in session.execute(
                    select(Item, Source.title).join(Source, Item.source_id == Source.id)
                    .where(Item.id.in_([entry.id for entry in inputs] + [id for id, _ in creator_updates]))
                )
            }
            saved_topics = [
                (topic, [item_id for item_id in topic.item_ids if item_id in items])
                for topic in topics
            ]
            saved_topics = [(topic, ids) for topic, ids in saved_topics if ids]
            saved_ids = [item_id for _, ids in saved_topics for item_id in ids]
            updates = [(item_id, reason) for item_id, reason in creator_updates if item_id in items]
            run = session.get(DigestRun, run_id)
            if not saved_ids and not updates:
                run.status = "no_new_content"
                run.finished_at = utc_now()
                _write_usage(run, usage)
                session.commit()
                return
            all_ids = saved_ids + [item_id for item_id, _ in updates]
            digest = Digest(run_id=run_id, model_id=model_id, item_count=len(all_ids),
                            source_count=len({items[item_id][0].source_id for item_id in all_ids}),
                            transcript_wait_days=app.state.settings.transcript_wait_days)
            session.add(digest)
            session.flush()
            for position, (topic, item_ids) in enumerate(saved_topics):
                saved_topic = DigestTopic(
                    digest_id=digest.id, position=position, title=topic.title, overview=topic.overview,
                )
                session.add(saved_topic)
                session.flush()
                for index, item_id in enumerate(item_ids):
                    item, source_name = items[item_id]
                    summary = summaries[item_id]
                    session.add(DigestItem(
                        digest_id=digest.id, topic_id=saved_topic.id, position=index,
                        item_id=item.id, title=item.title, link=item.link, source_name=source_name,
                        published_at=item.published_at, summary=summary.summary,
                        summary_unavailable=summary.unavailable,
                    ))
                    item.state = "delivered"
            if updates:
                creator_topic = DigestTopic(
                    digest_id=digest.id, position=len(saved_topics),
                    title="Creator updates", overview="", kind="creator_updates",
                )
                session.add(creator_topic)
                session.flush()
                updates.sort(key=lambda row: (
                    items[row[0]][1].casefold(),
                    items[row[0]][1],
                    -(items[row[0]][0].published_at.timestamp()
                      if items[row[0]][0].published_at else float("-inf")),
                    row[0],
                ))
                for position, (item_id, reason) in enumerate(updates):
                    item, source_name = items[item_id]
                    session.add(DigestItem(
                        digest_id=digest.id, topic_id=creator_topic.id, position=position,
                        item_id=item.id, title=item.title, link=item.link, source_name=source_name,
                        published_at=item.published_at, summary=None, summary_unavailable=False,
                        update_reason=reason,
                    ))
                    item.transcript_status = reason
                    item.state = "delivered"
            run.status = "succeeded"
            run.digest_id = digest.id
            run.finished_at = utc_now()
            _write_usage(run, usage)
            session.commit()
    except (AuthFailed, InsufficientBalance) as exc:
        _fail(factory, run_id, exc.code, f"{exc} Check the model settings.", usage)
    except ModelError as exc:
        _fail(factory, run_id, exc.code, str(exc), usage)
    except (AppError, InvalidToken):
        _fail(factory, run_id, "model_not_configured", "Check the model settings and instance secret.", usage)
    except Exception as exc:
        # Never expose provider credentials, URLs, or collected content in a run error.
        # Keep the traceback, but replace the exception text: provider errors can echo secrets.
        logger.exception(
            "Unexpected digest generation failure for run %s (%s)", run_id, type(exc).__name__,
            exc_info=(Exception, Exception("details withheld"), exc.__traceback__),
        )
        _fail(factory, run_id, "run_failed", "Digest generation failed. Try again.", usage)


def run_detail(session, run: DigestRun) -> dict:
    checks = session.execute(
        select(SourceCheck, Source.title).join(Source, SourceCheck.source_id == Source.id)
        .where(SourceCheck.run_id == run.id).order_by(SourceCheck.id)
    ).all()
    return {
        "id": run.id, "status": run.status, "items_total": run.items_total,
        "items_done": run.items_done, "error_kind": run.error_kind,
        "waiting_count": run.waiting_count, "deferred_count": run.deferred_count,
        "prompt_tokens": run.prompt_tokens, "completion_tokens": run.completion_tokens,
        "error_message": run.error_message, "digest_id": run.digest_id,
        "started_at": run.started_at, "finished_at": run.finished_at,
        "sources_total": session.scalar(select(func.count(Source.id))) or 0,
        "source_checks": [
            {"source_id": check.source_id, "source_title": title, "status": check.status,
             "possible_gap": check.possible_gap, "error": check.error,
             "http_status": check.http_status, "rate_limited": is_rate_limited(check)}
            for check, title in checks
        ],
    }
