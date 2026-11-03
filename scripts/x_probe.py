"""Probe the X API's response shapes for add-x-accounts (#41, design D11).

Run it yourself, with your own app-only Bearer token, from backend/:

    read -rs X_BEARER_TOKEN && export X_BEARER_TOKEN
    uv run python ../scripts/x_probe.py <public username> > ../work/x-probe.txt

It prints each response's status, rate-limit headers, and JSON structure, with
strings cut to 40 characters. It never prints the token or any request header.
It reads one account and at most 15 posts (about $0.09 at 2026-10-24 prices;
repeats within a UTC day are billed once).
"""

import json
import os
import sys

import httpx

API = "https://api.x.com"
USER_FIELDS = "id,name,username,protected,most_recent_tweet_id"
POST_FIELDS = ("created_at,conversation_id,in_reply_to_user_id,referenced_tweets,"
               "entities,note_tweet,attachments,author_id")
POST_FIELDS_NEW = POST_FIELDS.replace("note_tweet", "note_post").replace("referenced_tweets", "referenced_posts")
MEDIA = {"expansions": "attachments.media_keys",
         "media.fields": "media_key,type,url,alt_text,preview_image_url"}
RATE_HEADERS = ("x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset")


def shape(value, depth=0, limit=40):
    """Return the JSON structure with short strings and at most two list items."""
    if isinstance(value, dict):
        return {key: shape(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        items = [shape(item, depth + 1) for item in value[:2]]
        return items + ([f"... {len(value) - 2} more"] if len(value) > 2 else [])
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "..."
    return value


def call(client, label, path, params):
    try:
        response = client.get(path, params=params)
    except httpx.HTTPError as exc:
        print(f"## {label}\nrequest failed: {type(exc).__name__}\n")
        return None
    print(f"## {label}\nGET {path}  params={sorted(params)}\nstatus: {response.status_code}")
    for name in RATE_HEADERS:
        if name in response.headers:
            print(f"{name}: {response.headers[name]}")
    try:
        body = response.json()
    except ValueError:
        print(f"non-JSON body, {len(response.content)} bytes\n")
        return None
    print(json.dumps(shape(body), indent=2, ensure_ascii=False), "\n")
    return body


def keys_in(body, *names):
    found = set()

    def walk(value):
        if isinstance(value, dict):
            found.update(name for name in names if name in value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(body)
    return sorted(found)


def main(argv, client=None):
    if len(argv) != 2:
        print(__doc__)
        return 2
    username = argv[1].lstrip("@")
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token and client is None:
        print("Set X_BEARER_TOKEN in this shell first (see the usage above).")
        return 2
    client = client or httpx.Client(
        base_url=API, timeout=httpx.Timeout(15, connect=5),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "CatchUp x_probe"},
    )
    with client:
        user = call(client, "1. user lookup", f"/2/users/by/username/{username}",
                    {"user.fields": USER_FIELDS})
        user_id = ((user or {}).get("data") or {}).get("id")
        posts_old = posts_new = posts_replies = None
        if user_id:
            posts_old = call(client, "2. posts, tweet.fields spelling", f"/2/users/{user_id}/tweets",
                             {"max_results": 5, "exclude": "retweets,replies", "tweet.fields": POST_FIELDS, **MEDIA})
            posts_new = call(client, "3. posts, post.fields spelling", f"/2/users/{user_id}/tweets",
                             {"max_results": 5, "exclude": "retweets,replies", "post.fields": POST_FIELDS_NEW, **MEDIA})
            posts_replies = call(client, "4. posts with replies", f"/2/users/{user_id}/tweets",
                                 {"max_results": 5, "exclude": "retweets", "tweet.fields": POST_FIELDS, **MEDIA})
        usage = call(client, "5. usage", "/2/usage/tweets", {"days": 1})
        missing = call(client, "6. unknown user", "/2/users/by/username/zq_no_user_4417",
                       {"user.fields": USER_FIELDS})

    print("## Summary")
    print("lookup returns most_recent_tweet_id:", bool(keys_in(user, "most_recent_tweet_id")))
    print("tweet.fields spelling, long-post keys:", keys_in(posts_old, "note_tweet", "note_post") or "none in sample")
    print("post.fields spelling, long-post keys:", keys_in(posts_new, "note_tweet", "note_post") or "none in sample")
    print("tweet.fields spelling, reference keys:", keys_in(posts_old, "referenced_tweets", "referenced_posts"))
    print("post.fields spelling, reference keys:", keys_in(posts_new, "referenced_tweets", "referenced_posts"))
    print("reply fields seen:", keys_in(posts_replies, "in_reply_to_user_id", "conversation_id"))
    print("usage endpoint keys:", keys_in(usage, "data", "errors", "title") or "no JSON")
    print("unknown-user keys:", keys_in(missing, "errors", "data", "title", "type"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
