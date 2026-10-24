"""Gather bounded, optional public context before selecting digest items."""

import logging
from urllib.parse import urlsplit

from lxml import html
from sqlalchemy import select
from trafilatura import extract

from catchup.context.comments import author_replies
from catchup.context.links import related_links
from catchup.context.robots import RobotsCache
from catchup.models import DigestRun, Item, ItemContext, Source
from catchup.net.safe_fetch import FetchError, safe_fetch
from catchup.sources.feeds import EntryLink

logger = logging.getLogger(__name__)
EXHAUSTED = object()


def gather_context(factory, run_id: int, settings, spacer) -> None:
    budget = [settings.context_fetches_per_run]
    robots = RobotsCache(budget=budget, spacer=spacer)
    with factory() as session:
        rows = session.execute(
            select(Item, Source).join(Source, Item.source_id == Source.id)
            .where(Item.state == "pending", Item.context_status.is_(None),
                   Source.kind.in_(("feed", "podcast", "capture")))
            .order_by(Item.id)
        ).all()
        plan = []
        for item, source in rows:
            if source.kind == "podcast" and item.transcript_status != "text":
                continue
            site_url = (f"{urlsplit(item.link).scheme}://{urlsplit(item.link).netloc}"
                        if source.kind == "capture" else source.site_url)
            links = related_links(
                item.link, site_url,
                [EntryLink(**link) for link in (item.entry_links or [])],
                settings.links_per_item,
            )
            comments = bool(source.kind != "capture" and settings.author_replies
                            and item.comment_count and item.comment_count > 0)
            captured_replies = item.captured_replies or [] if source.kind == "capture" else []
            plan.append((item.id, site_url, links, comments, captured_replies))
        run = session.get(DigestRun, run_id)
        run.context_total = sum(
            len(links) + int(comments) + int(bool(replies))
            for _, _, links, comments, replies in plan
        )
        session.commit()

    def fetch(url):
        if budget[0] <= 0:
            return EXHAUSTED
        try:
            if not robots.allowed(url):
                return EXHAUSTED if budget[0] <= 0 else None
            if budget[0] <= 0:
                return EXHAUSTED
            return safe_fetch(url, budget=budget, spacer=spacer)
        except FetchError as exc:
            if budget[0] <= 0:
                return EXHAUSTED
            logger.info("Context fetch skipped (%s)", exc.code)
            return None
        except Exception as exc:
            logger.warning("Context fetch skipped (%s)", type(exc).__name__)
            return None

    def progress(*, done: int = 0, total: int = 0):
        with factory() as session:
            run = session.get(DigestRun, run_id)
            run.context_done += done
            run.context_total += total
            session.commit()

    for item_id, site_url, links, comments, captured_replies in plan:
        if budget[0] <= 0 and not captured_replies:
            continue
        with factory() as session:
            item = session.get(Item, item_id)
            if item is None:
                continue
            linked_length = 0
            position = 0
            stored_urls = set()
            attempted = False
            exhausted = False
            for link in links:
                if linked_length >= 16_000:
                    break
                if budget[0] <= 0:
                    exhausted = True
                    break
                response = fetch(link.url)
                if response is EXHAUSTED:
                    exhausted = True
                    break
                attempted = True
                progress(done=1)
                if response is None:
                    continue
                if not related_links(item.link, site_url, [EntryLink(response.url, link.text)], 1):
                    continue
                if response.url in stored_urls:
                    continue
                try:
                    text = extract(response.content, url=response.url)
                    if not text or not text.strip():
                        continue
                    document = html.fromstring(response.content)
                    titles = document.xpath("//title/text()")
                    title = titles[0].strip() if titles and titles[0].strip() else link.text
                    content = text.strip()[:min(3000, 16_000 - linked_length)]
                    linked_length += len(content)
                    position += 1
                    stored_urls.add(response.url)
                    session.add(ItemContext(
                        item_id=item.id, ref=f"L{position}", kind="link", url=response.url,
                        title=title, text=content, position=position,
                    ))
                except Exception as exc:
                    logger.warning("Context extraction skipped (%s)", type(exc).__name__)
            if comments:
                page = fetch(item.link)
                if page is EXHAUSTED:
                    exhausted = True
                else:
                    attempted = True
                    progress(done=1)
                if page is not None and page is not EXHAUSTED:
                    try:
                        reply_texts = author_replies(page.content, item.entry_author)
                        document = html.fromstring(page.content)
                        markup = document.xpath(
                            "//*[self::li or self::div][contains(concat(' ', normalize-space(@class), ' '), ' comment ')]"
                        )
                        if not markup and item.comment_feed_url:
                            progress(total=1)
                            feed = fetch(item.comment_feed_url)
                            if feed is EXHAUSTED:
                                exhausted = True
                            else:
                                progress(done=1)
                            if feed is not None and feed is not EXHAUSTED:
                                reply_texts = author_replies(page.content, item.entry_author, feed.content)
                        if reply_texts:
                            session.add(ItemContext(
                                item_id=item.id, ref="A1", kind="author_replies", url=page.url,
                                title=f"Author replies ({len(reply_texts)})",
                                text="\n\n".join(reply_texts), position=position + 1,
                            ))
                    except Exception as exc:
                        logger.warning("Comment extraction skipped (%s)", type(exc).__name__)
            if captured_replies:
                session.add(ItemContext(
                    item_id=item.id, ref="A1", kind="author_replies", url=item.link,
                    title=f"Author replies ({len(captured_replies)})",
                    text="\n\n".join(captured_replies), position=position + 1,
                ))
                progress(done=1)
                attempted = True
            with factory() as check_session:
                if check_session.get(Item, item_id) is None:
                    session.rollback()
                    continue
            if attempted or exhausted:
                session.flush()
                if item.contexts and item.summary is not None:
                    item.summary = None
                    item.summary_language = None
                item.context_status = "gathered" if item.contexts else "none"
            elif not links and not comments:
                item.context_status = "none"
            session.commit()
