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
                   Source.kind.in_(("feed", "podcast")))
            .order_by(Item.id)
        ).all()
        plan = []
        for item, source in rows:
            if source.kind == "podcast" and item.transcript_status != "text":
                continue
            links = related_links(
                item.link, source.site_url,
                [EntryLink(**link) for link in (item.entry_links or [])],
                settings.links_per_item,
            )
            comments = bool(settings.author_replies and item.comment_count and item.comment_count > 0)
            plan.append((item.id, source.site_url, links, comments))
        run = session.get(DigestRun, run_id)
        run.context_total = sum(len(links) + int(comments) for _, _, links, comments in plan)
        session.commit()

    def fetch(url):
        if budget[0] <= 0:
            return EXHAUSTED
        try:
            if not robots.allowed(url):
                return None
            if budget[0] <= 0:
                return EXHAUSTED
            return safe_fetch(url, budget=budget, spacer=spacer)
        except FetchError as exc:
            logger.info("Context fetch skipped (%s)", exc.code)
            return None
        except Exception as exc:
            logger.warning("Context fetch skipped (%s)", type(exc).__name__)
            return None

    for item_id, site_url, links, comments in plan:
        if budget[0] <= 0:
            break
        with factory() as session:
            item = session.get(Item, item_id)
            linked_length = 0
            position = 0
            attempted = False
            exhausted = False
            for link in links:
                if linked_length >= 16_000 or budget[0] <= 0:
                    exhausted = budget[0] <= 0
                    break
                response = fetch(link.url)
                if response is EXHAUSTED:
                    exhausted = True
                    break
                attempted = True
                session.get(DigestRun, run_id).context_done += 1
                if response is None:
                    continue
                if not related_links(item.link, site_url, [EntryLink(response.url, link.text)], 1):
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
                    session.add(ItemContext(
                        item_id=item.id, ref=f"L{position}", kind="link", url=response.url,
                        title=title, text=content, position=position,
                    ))
                except Exception as exc:
                    logger.warning("Context extraction skipped (%s)", type(exc).__name__)
            if comments and budget[0] > 0:
                attempted = True
                page = fetch(item.link)
                session.get(DigestRun, run_id).context_done += 1
                if page is not None:
                    try:
                        reply_texts = author_replies(page.content, item.entry_author)
                        document = html.fromstring(page.content)
                        markup = document.xpath(
                            "//*[self::li or self::div][contains(concat(' ', normalize-space(@class), ' '), ' comment ')]"
                        )
                        if not markup and item.comment_feed_url and budget[0] > 0:
                            session.get(DigestRun, run_id).context_total += 1
                            feed = fetch(item.comment_feed_url)
                            session.get(DigestRun, run_id).context_done += 1
                            if feed is not None:
                                reply_texts = author_replies(page.content, item.entry_author, feed.content)
                        if reply_texts:
                            session.add(ItemContext(
                                item_id=item.id, ref="A1", kind="author_replies", url=page.url,
                                title=f"Author replies ({len(reply_texts)})",
                                text="\n\n".join(reply_texts), position=position + 1,
                            ))
                    except Exception as exc:
                        logger.warning("Comment extraction skipped (%s)", type(exc).__name__)
            if exhausted and not item.contexts:
                item.context_status = None
            elif attempted:
                session.flush()
                item.context_status = "gathered" if item.contexts else "none"
            elif not links and not comments:
                item.context_status = "none"
            session.commit()
