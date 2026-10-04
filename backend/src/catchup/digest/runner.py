"""Single-instance digest lifecycle, with database writes on the runner thread."""

import logging
import threading
from contextlib import closing

from cryptography.fernet import InvalidToken
from fastapi import FastAPI
from sqlalchemy import func, select

from catchup.collection import check_source
from catchup.crypto import decrypt_key
from catchup.digest.group import GroupItem, group_items
from catchup.digest.summarize import SummaryInput, SummaryResult, summarize_items
from catchup.errors import AppError
from catchup.llm.client import AuthFailed, InsufficientBalance, ModelError
from catchup.models import (
    AppSettings, Digest, DigestItem, DigestRun, DigestTopic, Item, ModelConfig,
    Source, SourceCheck, utc_now,
)
from catchup.net.host_spacing import HostSpacer
from catchup.net.rate_limit import is_rate_limited

ACTIVE = ("queued", "collecting", "summarizing", "grouping")
_start_lock = threading.Lock()
logger = logging.getLogger(__name__)


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


def _fail(factory, run_id: int, kind: str, message: str) -> None:
    with factory() as session:
        run = session.get(DigestRun, run_id)
        run.status = "failed"
        run.error_kind = kind
        run.error_message = message
        run.finished_at = utc_now()
        session.commit()


def run_digest(app: FastAPI, run_id: int) -> None:
    """Synchronous entry point for tests; production calls it from a daemon thread."""
    factory = app.state.session_factory
    try:
        with factory() as session:
            config = session.get(ModelConfig, 1)
            if config is None:
                raise AppError("model_not_configured", "Set up a model in Settings before generating.")
            language_row = session.get(AppSettings, 1)
            language = language_row.digest_language if language_row else "en"
            # Configuration and language are read once, before any source check.
            base_url, model_id = config.base_url, config.model_id
            key = decrypt_key(config.api_key_encrypted, app.state.settings.secret_key)
            source_ids = session.scalars(select(Source.id).order_by(Source.id)).all()
        _stage(factory, run_id, "collecting")
        spacer = HostSpacer()
        for source_id in source_ids:
            with factory() as session:
                source = session.get(Source, source_id)
                if source is not None:
                    check_source(session, source, run_id, app.state.settings, spacer=spacer)

        with factory() as session:
            rows = session.execute(
                select(Item, Source.title).join(Source, Item.source_id == Source.id)
                .where(Item.state == "pending").order_by(Item.id)
            ).all()
            inputs = [
                SummaryInput(item.id, item.title, item.content_text, item.summary, item.summary_language)
                for item, _ in rows
            ]
            names = {item.id: name for item, name in rows}
        if not inputs:
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

        with closing(app.state.model_client_factory(base_url, key, model_id)) as client:
            summarize_items(client, inputs, language, app.state.settings.max_item_chars, record)
            _stage(factory, run_id, "grouping")
            with factory() as session:
                group_inputs = [
                    GroupItem(item.id, item.title, names[item.id], summaries[item.id].summary)
                    for item in session.scalars(
                        select(Item).where(Item.id.in_([entry.id for entry in inputs])).order_by(Item.id)
                    )
                ]
            topics = group_items(client, group_inputs, language, app.state.settings.grouping_batch_chars)

        # Snapshot and delivery share one transaction: a failed save cannot lose pending items.
        with factory() as session:
            items = {
                item.id: (item, source_name)
                for item, source_name in session.execute(
                    select(Item, Source.title).join(Source, Item.source_id == Source.id)
                    .where(Item.id.in_([entry.id for entry in inputs]))
                )
            }
            saved_topics = [
                (topic, [item_id for item_id in topic.item_ids if item_id in items])
                for topic in topics
            ]
            saved_topics = [(topic, ids) for topic, ids in saved_topics if ids]
            saved_ids = [item_id for _, ids in saved_topics for item_id in ids]
            run = session.get(DigestRun, run_id)
            if not saved_ids:
                run.status = "no_new_content"
                run.finished_at = utc_now()
                session.commit()
                return
            digest = Digest(run_id=run_id, model_id=model_id, item_count=len(saved_ids),
                            source_count=len({items[item_id][0].source_id for item_id in saved_ids}))
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
            run.status = "succeeded"
            run.digest_id = digest.id
            run.finished_at = utc_now()
            session.commit()
    except (AuthFailed, InsufficientBalance) as exc:
        _fail(factory, run_id, exc.code, f"{exc} Check the model settings.")
    except ModelError as exc:
        _fail(factory, run_id, exc.code, str(exc))
    except (AppError, InvalidToken):
        _fail(factory, run_id, "model_not_configured", "Check the model settings and instance secret.")
    except Exception as exc:
        # Never expose provider credentials, URLs, or collected content in a run error.
        # Keep the traceback, but replace the exception text: provider errors can echo secrets.
        logger.exception(
            "Unexpected digest generation failure for run %s (%s)", run_id, type(exc).__name__,
            exc_info=(Exception, Exception("details withheld"), exc.__traceback__),
        )
        _fail(factory, run_id, "run_failed", "Digest generation failed. Try again.")


def run_detail(session, run: DigestRun) -> dict:
    checks = session.execute(
        select(SourceCheck, Source.title).join(Source, SourceCheck.source_id == Source.id)
        .where(SourceCheck.run_id == run.id).order_by(SourceCheck.id)
    ).all()
    return {
        "id": run.id, "status": run.status, "items_total": run.items_total,
        "items_done": run.items_done, "error_kind": run.error_kind,
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
