"""Transactional X account check with an explicit shared read budget."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from catchup.models import Item, Source, SourceCheck, XAccount, utc_now
from catchup.sources.x_accounts import post_item
from catchup.sources.x_api import XApiError, XClient, XPage, XPost, XUser


@dataclass
class XReadBudget:
    remaining: int
    reads: int = 0

    def charge(self, count: int) -> None:
        self.remaining -= count
        self.reads += count


def _replies(posts: list[XPost], root_id: str) -> list[str]:
    texts: list[str] = []
    for post in sorted((post for post in posts if post.is_reply and not post.is_retweet
                        and post.conversation_id == root_id), key=lambda post: post.created_at):
        if len(texts) == 10:
            break
        remaining = 4000 - len("\n\n".join(texts)) - (2 if texts else 0)
        if remaining <= 0:
            break
        texts.append(post.text[:remaining])
    return texts


def check_x_account(session: Session, source: Source, account: XAccount, run_id: int,
                    client: XClient, budget: XReadBudget) -> SourceCheck:
    """Read one account, committing its ids and items together or recording one failure."""
    if budget.remaining < 5:
        check = SourceCheck(
            run_id=run_id, source_id=source.id, status="deferred", entries_seen=0,
            new_count=0, checked_at=utc_now(),
        )
        source.last_check_status = "deferred"
        session.add(check)
        session.commit()
        return check

    old_newest = account.newest_id
    posts: list[XPost] = []
    entries_seen = 0

    def read_phase(*, since_id: str | None, until_id: str | None,
                   start_time, gap: bool) -> bool:
        nonlocal entries_seen
        token = None
        while budget.remaining >= 5:
            page: XPage = client.user_posts(
                account.user_id, since_id=since_id, until_id=until_id,
                start_time=start_time, max_results=min(100, budget.remaining),
                pagination_token=token, exclude=["retweets"],
            )
            budget.charge(page.result_count)
            entries_seen += page.result_count
            posts.extend(page.posts)
            oldest = min((post.id for post in page.posts), key=int, default=None)
            if gap:
                if oldest is not None:
                    account.gap_until_id = oldest
            else:
                newest = max((post.id for post in page.posts), key=int, default=None)
                if newest is not None and (account.newest_id is None or int(newest) > int(account.newest_id)):
                    account.newest_id = newest
                if page.next_token and oldest is not None:
                    account.gap_since_id = old_newest
                    account.gap_until_id = oldest
            if not page.next_token:
                if gap:
                    account.gap_since_id = account.gap_until_id = None
                return True
            if budget.remaining < 5:
                return False
            token = page.next_token
        return False

    try:
        if account.gap_until_id is not None:
            read_phase(
                since_id=account.gap_since_id, until_id=account.gap_until_id,
                start_time=account.followed_at if account.gap_since_id is None else None,
                gap=True,
            )
        if account.gap_until_id is None and budget.remaining >= 5:
            read_phase(
                since_id=old_newest, until_id=None,
                start_time=account.followed_at if old_newest is None else None,
                gap=False,
            )
        user = XUser(account.user_id, source.title, account.username, False, account.newest_id)
        keys = set(session.scalars(select(Item.identity_key).where(Item.source_id == source.id)))
        originals = [post for post in posts if not post.is_reply and not post.is_retweet]
        new_count = 0
        for post in originals:
            if post.id not in keys:
                session.add(post_item(post, source_id=source.id, user=user, replies=_replies(posts, post.id) or None))
                keys.add(post.id)
                new_count += 1
        now = utc_now()
        check = SourceCheck(
            run_id=run_id, source_id=source.id, status="new_items" if new_count else "no_new_items",
            http_status=200, entries_seen=entries_seen, new_count=new_count, checked_at=now,
        )
        session.add(check)
        source.last_check_at = now
        source.last_check_status = check.status
        session.commit()
        return check
    except XApiError as exc:
        session.rollback()
        now = utc_now()
        source = session.get(Source, source.id)
        check = SourceCheck(
            run_id=run_id, source_id=source.id, status="failed",
            error=str(exc), http_status=exc.http_status, entries_seen=entries_seen,
            new_count=0, checked_at=now,
        )
        source.last_check_at = now
        source.last_check_status = "failed"
        session.add(check)
        session.commit()
        return check
