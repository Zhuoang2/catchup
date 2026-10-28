"""Fixed-host X API transport for the user's own Bearer token."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from math import ceil

import httpx

from catchup.net.safe_fetch import MAX_BYTES, RATE_LIMIT_PREFIX, user_agent


USER_FIELDS = "id,name,username,protected,most_recent_tweet_id"
POST_FIELDS = (
    "created_at,conversation_id,in_reply_to_user_id,referenced_tweets,entities,"
    "note_tweet,attachments,author_id"
)
MEDIA_FIELDS = "media_key,type,url,alt_text,preview_image_url"


@dataclass(frozen=True)
class XUser:
    id: str
    name: str
    username: str
    protected: bool
    most_recent_post_id: str | None


@dataclass(frozen=True)
class XPhoto:
    url: str
    alt: str


@dataclass(frozen=True)
class XPost:
    id: str
    text: str
    created_at: datetime
    conversation_id: str | None
    in_reply_to_user_id: str | None
    is_retweet: bool
    is_reply: bool
    urls: tuple[str, ...]
    photos: tuple[XPhoto, ...]


@dataclass(frozen=True)
class XPage:
    posts: tuple[XPost, ...]
    next_token: str | None
    result_count: int


class XApiError(Exception):
    def __init__(self, code: str, message: str, http_status: int | None = None,
                 retry_after: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.retry_after = retry_after


class XClient:
    def __init__(self, token: str):
        self._client = httpx.Client(
            base_url="https://api.x.com", follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(15, connect=5),
            headers={"Authorization": f"Bearer {token}", "User-Agent": user_agent()},
        )

    def __enter__(self) -> "XClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, path: str, params: dict | None = None) -> dict:
        try:
            with self._client.stream("GET", path, params=params) as response:
                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise XApiError("fetch_failed", "X returned too much data.", response.status_code)
                    chunks.append(chunk)
                try:
                    body = json.loads(b"".join(chunks))
                except ValueError:
                    body = {}
                errors = body.get("errors", []) if isinstance(body, dict) else []
                for error in errors:
                    kind = str(error.get("type", "")).rsplit("/", 1)[-1].lower()
                    detail = str(error.get("detail", "")).lower()
                    if kind == "resource-not-found":
                        raise XApiError("x_account_not_found", "X account not found.", response.status_code)
                    if "suspend" in kind or "suspend" in detail:
                        raise XApiError("x_account_suspended", "X account suspended.", response.status_code)
                    if (("authoriz" in kind or "protect" in kind or "protect" in detail)
                            and (error.get("resource_type") == "user" or "account" in detail)):
                        raise XApiError("x_account_protected", "This X account is protected.", response.status_code)
                if response.status_code == 404:
                    raise XApiError("x_account_not_found", "X account not found.", response.status_code)
                if response.status_code in (401, 403):
                    raise XApiError("x_token_rejected", "X rejected the token.", response.status_code)
                if response.status_code == 429:
                    try:
                        delay = max(1, ceil(int(response.headers["x-rate-limit-reset"]) -
                                            datetime.now(timezone.utc).timestamp()))
                    except (KeyError, ValueError):
                        delay = 1
                    raise XApiError("rate_limited", f"{RATE_LIMIT_PREFIX} Try again later.",
                                    response.status_code, delay)
                if response.status_code >= 400:
                    raise XApiError("fetch_failed", "X could not complete the request.", response.status_code)
                if not isinstance(body, dict):
                    raise XApiError("fetch_failed", "X returned an invalid answer.", response.status_code)
                return body
        except httpx.HTTPError as exc:
            raise XApiError("fetch_failed", "Could not reach X.") from exc

    def usage(self) -> None:
        self._request("/2/usage/tweets", {"days": 1})

    def lookup_user(self, username: str) -> XUser:
        return self._parse_user(self._request(
            f"/2/users/by/username/{username}", {"user.fields": USER_FIELDS},
        ))

    def lookup_user_by_id(self, user_id: str) -> XUser:
        return self._parse_user(self._request(f"/2/users/{user_id}", {"user.fields": USER_FIELDS}))

    @staticmethod
    def _parse_user(body: dict) -> XUser:
        user = body.get("data")
        if not isinstance(user, dict):
            raise XApiError("fetch_failed", "X returned no account data.")
        try:
            return XUser(str(user["id"]), str(user["name"]), str(user["username"]),
                         bool(user.get("protected", False)),
                         user.get("most_recent_tweet_id") or user.get("most_recent_post_id"))
        except (KeyError, TypeError) as exc:
            raise XApiError("fetch_failed", "X returned invalid account data.") from exc

    def user_posts(
        self, user_id: str, *, since_id: str | None = None, until_id: str | None = None,
        start_time: datetime | None = None, max_results: int = 5,
        pagination_token: str | None = None, exclude: list[str] | None = None,
    ) -> XPage:
        params: dict[str, str | int] = {
            "max_results": max_results, "tweet.fields": POST_FIELDS,
            "expansions": "attachments.media_keys", "media.fields": MEDIA_FIELDS,
        }
        if since_id is not None:
            params["since_id"] = since_id
        if until_id is not None:
            params["until_id"] = until_id
        if start_time is not None:
            params["start_time"] = start_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if pagination_token is not None:
            params["pagination_token"] = pagination_token
        if exclude:
            params["exclude"] = ",".join(exclude)
        body = self._request(f"/2/users/{user_id}/tweets", params)
        media = {entry["media_key"]: entry for entry in body.get("includes", {}).get("media", [])
                 if entry.get("media_key")}
        try:
            posts = tuple(self._parse_post(post, media) for post in body.get("data", []))
            meta = body.get("meta", {})
            return XPage(posts, meta.get("next_token"), int(meta.get("result_count", len(posts))))
        except (ValueError, KeyError, TypeError) as exc:
            raise XApiError("fetch_failed", "X returned invalid post data.") from exc

    @staticmethod
    def _parse_post(data: dict, media: dict) -> XPost:
        note = data.get("note_tweet") or data.get("note_post") or {}
        text = note.get("text") or data.get("text", "")
        entities = note.get("entities") or data.get("entities") or {}
        urls = []
        for link in entities.get("urls", []):
            destination = link.get("unwound_url") or link.get("expanded_url")
            if destination:
                text = text.replace(link.get("url", ""), destination)
                urls.append(destination)
        references = data.get("referenced_tweets") or data.get("referenced_posts") or []
        types = {entry.get("type") for entry in references}
        photos = tuple(XPhoto(media[key]["url"], media[key].get("alt_text") or "")
                       for key in data.get("attachments", {}).get("media_keys", ())
                       if key in media and media[key].get("type") == "photo" and media[key].get("url"))
        return XPost(
            id=str(data["id"]), text=text,
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            conversation_id=data.get("conversation_id"),
            in_reply_to_user_id=data.get("in_reply_to_user_id"),
            is_retweet="retweeted" in types,
            is_reply="replied_to" in types or bool(data.get("in_reply_to_user_id")),
            urls=tuple(urls), photos=photos,
        )
