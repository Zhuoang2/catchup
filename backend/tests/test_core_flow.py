"""Exercise the public API from configuration through incremental digest history."""

import socket
from dataclasses import replace
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from catchup.api.settings import get_model_client_factory
from catchup.digest.runner import run_digest, start_run
from catchup.main import create_app
from catchup.llm.client import ModelInfo
from test_digest_runner import FakeModel

FEED_URL = "https://site.example/feed.xml"
FIXTURE = Path(__file__).parent / "fixtures" / "rss.xml"


class FixtureModel(FakeModel):
    def list_models(self):
        return [ModelInfo("fixture-model")]

    def usage_totals(self):
        return None


def test_incremental_api_flow_with_stored_citations(test_settings, monkeypatch):
    def public_dns(_host, port, *_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]

    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    settings = replace(test_settings, secret_key="test-only-instance-secret", short_text_chars=0)
    app = create_app(settings)
    model = FixtureModel()
    app.dependency_overrides[get_model_client_factory] = lambda: lambda *_: model
    app.state.model_client_factory = lambda *_: model
    current_feed = FIXTURE.read_bytes()

    def feed_response(_request):
        return httpx.Response(
            200, content=current_feed, headers={"content-type": "application/rss+xml"},
        )

    def generate(client):
        # The same synchronous entry point as the background worker, without polling or sleeps.
        run = start_run(client.app, background=False)
        run_digest(client.app, run.id)
        response = client.get(f"/api/digest-runs/{run.id}")
        assert response.status_code == 200
        return response.json()

    with TestClient(app) as client, respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(side_effect=feed_response)
        tested = client.post("/api/settings/model/test", json={
            "base_url": "https://model.example/v1", "api_key": "test-only-key",
        })
        assert tested.json() == {"ok": True, "models": ["fixture-model"]}
        saved = client.put("/api/settings/model", json={
            "base_url": "https://model.example/v1", "api_key": "test-only-key",
            "model_id": tested.json()["models"][0],
        })
        assert saved.status_code == 200 and saved.json()["key_set"]
        assert "test-only-key" not in saved.text

        preview = client.post("/api/sources/preview", json={"url": FEED_URL})
        assert preview.status_code == 200
        assert preview.json()["title"] == "Example News"
        assert {entry["link"] for entry in preview.json()["entries"]} == {
            "https://site.example/a", "https://site.example/b",
        }
        confirmed = client.post("/api/sources", json={"feed_url": preview.json()["feed_url"]})
        assert confirmed.status_code == 201
        assert confirmed.json()["last_check_status"] == "new_items"

        first = generate(client)
        assert first["status"] == "succeeded"
        assert (first["items_total"], first["items_done"]) == (2, 2)
        assert first["source_checks"][0]["status"] == "no_new_items"
        first_digest = client.get(f"/api/digests/{first['digest_id']}").json()
        first_items = [item for topic in first_digest["topics"] for item in topic["items"]]
        assert {item["link"] for item in first_items} == {
            "https://site.example/a", "https://site.example/b",
        }
        assert {item["source_name"] for item in first_items} == {"Example News"}

        second = generate(client)
        assert second["status"] == "no_new_content" and second["digest_id"] is None
        assert second["source_checks"][0]["status"] == "no_new_items"
        assert len(client.get("/api/digests").json()) == 1

        new_entry = (
            b"<item><guid>entry-c</guid><title>Third</title>"
            b"<link>https://site.example/c</link>"
            b"<pubDate>Sat, 03 Oct 2026 10:00:00 GMT</pubDate>"
            b"<description>New story.</description></item>"
        )
        current_feed = current_feed.replace(b"</channel>", new_entry + b"</channel>")
        third = generate(client)
        assert third["status"] == "succeeded"
        assert (third["items_total"], third["items_done"]) == (1, 1)
        assert third["source_checks"][0]["status"] == "new_items"
        third_digest = client.get(f"/api/digests/{third['digest_id']}").json()
        third_items = [item for topic in third_digest["topics"] for item in topic["items"]]
        assert [(item["title"], item["link"], item["source_name"]) for item in third_items] == [
            ("Third", "https://site.example/c", "Example News"),
        ]
        assert len(client.get("/api/digests").json()) == 2
        assert client.get(f"/api/digests/{first['digest_id']}").json() == first_digest
        assert len(model.calls) == 5  # Three item summaries and two grouping calls.
        assert router.calls.call_count == 4  # Preview feed reused at confirm, plus three checks.
