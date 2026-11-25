"""Gather bounded, optional public context before selecting digest items."""

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urlsplit

from lxml import html
from sqlalchemy import select
from trafilatura import extract

from catchup.context.comments import author_replies
from catchup.context.depth import context_limits
from catchup.context.links import related_links
from catchup.context.robots import RobotsCache, origin
from catchup.models import DigestRun, Item, ItemContext, Source
from catchup.net.safe_fetch import BudgetExhausted, FetchError, safe_fetch
from catchup.sources.feeds import EntryLink

logger = logging.getLogger(__name__)
CONTEXT_WORKERS = 4


def reachable_reads(urls, verdict, units: int) -> int:
    charged = set()
    count = 0
    for url in urls:
        try:
            site = origin(url)
        except ValueError:
            count += 1
            continue
        rule = verdict(url)
        if rule is False:
            cost = 0
        elif rule is True or site in charged:
            cost = 1
        else:
            cost = 2
        if cost > units:
            break
        units -= cost
        charged.add(site)
        count += 1
    return count


class ContextProgress:
    def __init__(self, factory, run_id, remaining, replies_left, robots, budget):
        self.factory = factory
        self.run_id = run_id
        self.remaining = remaining
        self.replies_left = set(replies_left)
        self.robots = robots
        self.budget = budget
        self.in_progress = {}
        self.done = 0
        self.lock = Lock()
        self._commit()

    def _commit(self):
        urls = [url for reads in self.remaining.values() for _, url in reads]
        total = (
            self.done + len(self.in_progress) + len(self.replies_left)
            + reachable_reads(urls, self.robots.verdict, self.budget[0])
        )
        with self.factory() as session:
            run = session.get(DigestRun, self.run_id)
            run.context_done, run.context_total = self.done, total
            session.commit()

    def start(self, item_id):
        with self.lock:
            self.in_progress[item_id] = self.remaining[item_id].pop(0)

    def finish(self, item_id):
        with self.lock:
            self.in_progress.pop(item_id)
            self.done += 1
            self._commit()

    def drop_links(self, item_id):
        with self.lock:
            self.remaining[item_id] = [
                read for read in self.remaining[item_id] if read[0] != "link"
            ]
            self._commit()

    def drop(self, item_id, *, deleted=False):
        with self.lock:
            self.remaining[item_id] = []
            self.in_progress.pop(item_id, None)
            if deleted:
                self.replies_left.discard(item_id)
            self._commit()

    def add(self, item_id, url):
        with self.lock:
            self.remaining[item_id].append(("feed", url))
            self._commit()

    def replies(self, item_id):
        with self.lock:
            self.replies_left.remove(item_id)
            self.done += 1
            self._commit()


def gather_context(factory, run_id: int, settings, spacer, level="normal") -> None:
    limits = context_limits(level, settings)
    budget = [limits.fetches_per_run]
    robots = RobotsCache(budget=budget, spacer=spacer)
    with factory() as session:
        rows = session.execute(
            select(Item, Source).join(Source, Item.source_id == Source.id)
            .where(Item.state == "pending", Item.context_status.is_(None),
                   Source.kind.in_(("feed", "podcast", "capture", "x")))
            .order_by(Item.id)
        ).all()
        plan = []
        remaining = {}
        replies_left = []
        for item, source in rows:
            if source.kind == "podcast" and item.transcript_status != "text":
                continue
            site_url = (f"{urlsplit(item.link).scheme}://{urlsplit(item.link).netloc}"
                        if source.kind in ("capture", "x") else source.site_url)
            links = related_links(
                item.link, site_url,
                [EntryLink(**link) for link in (item.entry_links or [])],
                limits.links_per_item,
            )
            comments = bool(source.kind not in ("capture", "x") and limits.author_replies
                            and item.comment_count and item.comment_count > 0)
            captured_replies = item.captured_replies or [] if source.kind in ("capture", "x") else []
            plan.append((item.id, site_url, links, comments, captured_replies))
            remaining[item.id] = (
                [("link", link.url) for link in links]
                + ([("post", item.link)] if comments else [])
            )
            if captured_replies:
                replies_left.append(item.id)
    progress = ContextProgress(factory, run_id, remaining, replies_left, robots, budget)

    def fetch(url):
        try:
            return safe_fetch(url, budget=budget, spacer=spacer, allow=robots.allowed)
        except BudgetExhausted:
            raise
        except FetchError as exc:
            logger.info("Context fetch skipped (%s)", exc.code)
            return None
        except Exception as exc:
            logger.warning("Context fetch skipped (%s)", type(exc).__name__)
            return None

    def gather_item(entry):
        item_id, site_url, links, comments, captured_replies = entry
        if budget[0] <= 0 and not captured_replies:
            progress.drop(item_id)
            return
        with factory() as session:
            item = session.get(Item, item_id)
            if item is None:
                progress.drop(item_id, deleted=True)
                return
            linked_length = 0
            position = 0
            stored_urls = set()
            try:
                for link in links:
                    if linked_length >= 16_000:
                        progress.drop_links(item_id)
                        break
                    progress.start(item_id)
                    response = fetch(link.url)
                    progress.finish(item_id)
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
                    progress.start(item_id)
                    page = fetch(item.link)
                    progress.finish(item_id)
                    if page is not None:
                        try:
                            def fetch_feed():
                                progress.add(item_id, item.comment_feed_url)
                                progress.start(item_id)
                                feed = fetch(item.comment_feed_url)
                                progress.finish(item_id)
                                return feed.content if feed is not None else None

                            reply_texts = author_replies(
                                page.content, item.entry_author,
                                fetch_feed=fetch_feed if item.comment_feed_url else None,
                            )
                            if reply_texts:
                                session.add(ItemContext(
                                    item_id=item.id, ref="A1", kind="author_replies", url=page.url,
                                    title=f"Author replies ({len(reply_texts)})",
                                    text="\n\n".join(reply_texts), position=position + 1,
                                ))
                        except BudgetExhausted:
                            raise
                        except Exception as exc:
                            logger.warning("Comment extraction skipped (%s)", type(exc).__name__)
            except BudgetExhausted:
                progress.drop(item_id)
            if captured_replies:
                session.add(ItemContext(
                    item_id=item.id, ref="A1", kind="author_replies", url=item.link,
                    title=f"Author replies ({len(captured_replies)})",
                    text="\n\n".join(captured_replies), position=position + 1,
                ))
                progress.replies(item_id)
            with factory() as check_session:
                if check_session.get(Item, item_id) is None:
                    session.rollback()
                    progress.drop(item_id, deleted=True)
                    return
            session.flush()
            if item.contexts and item.summary is not None:
                item.summary = None
                item.summary_language = None
            item.context_status = "gathered" if item.contexts else "none"
            session.commit()

    with ThreadPoolExecutor(max_workers=CONTEXT_WORKERS) as pool:
        futures = [pool.submit(gather_item, entry) for entry in plan]
        try:
            for future in futures:
                future.result()
        except Exception:
            pool.shutdown(wait=True, cancel_futures=True)
            raise
