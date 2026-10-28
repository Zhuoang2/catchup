"""Public X client boundary, using invented probe-shaped API responses."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from catchup.net.safe_fetch import MAX_BYTES, RATE_LIMIT_PREFIX
from catchup.sources.x_api import XApiError, XClient

TOKEN = "test-" + "x" * 40
USER = {"data": {"id": "1234567890123456789", "name": "Sample Writer", "username": "writer",
                 "protected": False, "most_recent_tweet_id": "1234567890123456999"}}
POST = {"id": "1234567890123456999", "text": "Short https://t.co/abc", "author_id": USER["data"]["id"],
        "created_at": "2026-10-27T04:18:22.000Z", "conversation_id": "1234567890123456999",
        "entities": {"urls": [{"url": "https://t.co/abc", "expanded_url": "https://old.example/post",
                                "unwound_url": "https://blog.example/post"}]},
        "attachments": {"media_keys": ["3_123"]}}

INVALID_TIMELINES = [
    httpx.Response(200, text="<html>Not a timeline</html>"),
    httpx.Response(200, json={"errors": [
        {"type": "https://api.x.com/2/problems/invalid-request"}]}),
    httpx.Response(200, json={"data": [POST]}),
]


@pytest.mark.parametrize("response", INVALID_TIMELINES, ids=["html", "unknown-error", "no-meta"])
def test_invalid_timeline_is_fetch_failed_with_status(response):
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
            side_effect=[response, AssertionError("unexpected second timeline request")])
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.user_posts(USER["data"]["id"])
        assert route.call_count == 1
    assert error.value.code == "fetch_failed"
    assert error.value.http_status == 200


def test_lookups_parse_user_fields_and_send_requested_fields():
    with respx.mock(assert_all_mocked=True) as router:
        by_name = router.get("https://api.x.com/2/users/by/username/writer").mock(
            return_value=httpx.Response(200, json=USER))
        by_id = router.get(f"https://api.x.com/2/users/{USER['data']['id']}").mock(
            return_value=httpx.Response(200, json=USER))
        with XClient(TOKEN) as client:
            first = client.lookup_user("writer")
            second = client.lookup_user_by_id(USER["data"]["id"])
    assert first == second
    assert (first.id, first.name, first.username, first.protected, first.most_recent_post_id) == (
        USER["data"]["id"], "Sample Writer", "writer", False, "1234567890123456999",
    )
    for route in (by_name, by_id):
        request = route.calls[0].request
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert set(request.url.params["user.fields"].split(",")) >= {
            "id", "name", "username", "protected", "most_recent_tweet_id",
        }


def test_posts_request_fields_pagination_long_text_links_and_photos():
    original = {**POST, "note_tweet": {"text": "Long https://t.co/abc"}}
    reply = {**POST, "id": "1234567890123456998", "text": "Reply https://t.co/abc",
             "conversation_id": original["id"], "in_reply_to_user_id": USER["data"]["id"],
             "referenced_tweets": [{"type": "replied_to", "id": original["id"]}]}
    repost = {**POST, "id": "1234567890123456997", "referenced_tweets": [
        {"type": "retweeted", "id": "1234567890123456000"}]}
    response = {"data": [original, reply, repost], "includes": {"media": [
        {"media_key": "3_123", "type": "photo", "url": "https://pbs.twimg.com/media/photo.jpg",
         "alt_text": "A chart"}]},
        "meta": {"result_count": 3, "next_token": "next"}}
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
            return_value=httpx.Response(200, json=response))
        with XClient(TOKEN) as client:
            page = client.user_posts(USER["data"]["id"], since_id="1", until_id="2",
                                     start_time=datetime(2026, 10, 20, tzinfo=timezone.utc),
                                     max_results=5, pagination_token="old", exclude=["retweets", "replies"])
    params = route.calls[0].request.url.params
    assert {key: params[key] for key in ("since_id", "until_id", "max_results", "pagination_token",
                                         "exclude")} == {
        "since_id": "1", "until_id": "2", "max_results": "5", "pagination_token": "old",
        "exclude": "retweets,replies",
    }
    assert params["start_time"].startswith("2026-10-20")
    assert set(params["tweet.fields"].split(",")) >= {
        "created_at", "conversation_id", "in_reply_to_user_id", "referenced_tweets",
        "entities", "note_tweet", "attachments", "author_id",
    }
    assert params["expansions"] == "attachments.media_keys"
    assert set(params["media.fields"].split(",")) >= {
        "media_key", "type", "url", "alt_text", "preview_image_url",
    }
    assert "referenced_tweets.id" not in str(route.calls[0].request.url)
    assert page.next_token == "next" and page.result_count == 3
    assert page.posts[0].text == "Long https://blog.example/post"
    assert page.posts[0].urls == ("https://blog.example/post",)
    assert page.posts[0].photos[0].alt == "A chart"
    assert page.posts[1].is_reply and not page.posts[1].is_retweet
    assert page.posts[2].is_retweet
    assert page.posts[0].created_at == datetime(2026, 10, 27, 4, 18, 22, tzinfo=timezone.utc)


@pytest.mark.parametrize(("note", "expected"), [
    ({"note_post": {"text": "Alternate long"}}, "Alternate long"),
    ({}, "Short https://blog.example/post"),
])
def test_post_text_fallbacks(note, expected):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
            return_value=httpx.Response(200, json={"data": [{**POST, **note}], "meta": {"result_count": 1}}))
        with XClient(TOKEN) as client:
            assert client.user_posts(USER["data"]["id"], max_results=5).posts[0].text == expected


@pytest.mark.parametrize(("status", "body", "code"), [
    (401, {}, "x_token_rejected"), (403, {}, "x_token_rejected"),
    (404, {}, "x_account_not_found"),
    (200, {"errors": [{"type": "https://api.x.com/2/problems/resource-not-found",
                        "resource_type": "user", "title": "Not Found Error"}]}, "x_account_not_found"),
    (200, {"errors": [{"type": "https://api.x.com/2/problems/user-suspended",
                        "detail": "User suspended"}]}, "x_account_suspended"),
    (500, {}, "fetch_failed"),
])
def test_lookup_error_mapping(status, body, code):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://api.x.com/2/users/by/username/writer").mock(
            return_value=httpx.Response(status, json=body))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.lookup_user("writer")
    assert error.value.code == code
    assert error.value.http_status == status


def test_protected_timeline_authorization_error_precedes_generic_token_error():
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
            return_value=httpx.Response(403, json={"errors": [
                {"type": "https://api.x.com/2/problems/not-authorized-for-resource",
                 "resource_type": "user", "detail": "This account is protected."}]}))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.user_posts(USER["data"]["id"], max_results=5)
    assert error.value.code == "x_account_protected"


def test_rate_limit_reset_and_other_http_errors():
    reset = int((datetime.now(timezone.utc) + timedelta(seconds=30)).timestamp())
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://api.x.com/2/usage/tweets").mock(
            return_value=httpx.Response(429, headers={"x-rate-limit-reset": str(reset)}))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.usage()
    assert error.value.code == "rate_limited"
    assert error.value.http_status == 429
    assert 1 <= error.value.retry_after <= 30
    assert str(error.value).startswith(RATE_LIMIT_PREFIX)


def test_body_limit_and_transport_failure_have_no_retry():
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://api.x.com/2/usage/tweets").mock(
            return_value=httpx.Response(200, content=b"x" * (MAX_BYTES + 1)))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.usage()
        assert error.value.code == "fetch_failed"
        assert route.call_count == 1
        route.mock(side_effect=httpx.ConnectError("connection refused"))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.usage()
        assert error.value.code == "fetch_failed" and error.value.http_status is None
        assert route.call_count == 2


@pytest.mark.parametrize("kind", ["lookup", "timeline"])
def test_partial_resource_not_found_error_does_not_discard_valid_data(kind):
    data = USER if kind == "lookup" else {"data": [POST], "meta": {"result_count": 1}}
    body = {**data, "errors": [{"type": "https://api.x.com/2/problems/resource-not-found",
                                  "detail": "Pinned post or media not found"}]}
    with respx.mock(assert_all_mocked=True) as router:
        if kind == "lookup":
            router.get("https://api.x.com/2/users/by/username/writer").mock(
                return_value=httpx.Response(200, json=body))
        else:
            router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
                return_value=httpx.Response(200, json=body))
        with XClient(TOKEN) as client:
            result = client.lookup_user("writer") if kind == "lookup" else client.user_posts(USER["data"]["id"])
    expected = USER["data"]["id"] if kind == "lookup" else POST["id"]
    assert (result.id if kind == "lookup" else result.posts[0].id) == expected


@pytest.mark.parametrize("status", [200, 403])
def test_suspension_detail_precedes_resource_not_found_and_http_status(status):
    body = {"errors": [{"type": "https://api.x.com/2/problems/resource-not-found",
                        "title": "Forbidden", "detail": "User has been suspended: [writer]."}]}
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://api.x.com/2/users/by/username/writer").mock(
            return_value=httpx.Response(status, json=body))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.lookup_user("writer")
    assert (error.value.code, error.value.http_status) == ("x_account_suspended", status)


def test_suspension_in_title_precedes_resource_not_found_with_misleading_detail():
    body = {"errors": [{"type": "https://api.x.com/2/problems/resource-not-found",
                        "title": "Account suspended",
                        "detail": "Could not find user with username: [name]."}]}
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://api.x.com/2/users/by/username/writer").mock(
            return_value=httpx.Response(200, json=body))
        with XClient(TOKEN) as client, pytest.raises(XApiError) as error:
            client.lookup_user("writer")
    assert (error.value.code, error.value.http_status) == ("x_account_suspended", 200)


def test_url_entity_without_short_url_keeps_text_but_includes_destination():
    post = {**POST, "text": "See the original", "entities": {"urls": [
        {"expanded_url": "https://blog.example/post"}]}}
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
            return_value=httpx.Response(200, json={"data": [post], "meta": {"result_count": 1}}))
        with XClient(TOKEN) as client:
            result = client.user_posts(USER["data"]["id"]).posts[0]
    assert result.text == "See the original"
    assert result.urls == ("https://blog.example/post",)


@pytest.mark.parametrize("signal", [
    {"referenced_tweets": [{"type": "replied_to", "id": "1"}]},
    {"in_reply_to_user_id": "123"},
])
def test_either_reply_signal_alone_marks_post_as_reply(signal):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"https://api.x.com/2/users/{USER['data']['id']}/tweets").mock(
            return_value=httpx.Response(200, json={"data": [{**POST, **signal}], "meta": {"result_count": 1}}))
        with XClient(TOKEN) as client:
            assert client.user_posts(USER["data"]["id"]).posts[0].is_reply
