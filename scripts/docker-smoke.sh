#!/usr/bin/env bash
set -euo pipefail

image="${1:?Usage: scripts/docker-smoke.sh IMAGE_TAG}"
name="catchup-smoke-$$"
volume="$name-data"
port="$(python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"

cleanup() {
    docker rm -f "$name" >/dev/null 2>&1 || true
    docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker volume create "$volume" >/dev/null
docker run -d --name "$name" --mount "type=volume,source=$volume,target=/data" \
    -p "127.0.0.1:$port:8000" "$image" >/dev/null

deadline=$(( $(date +%s) + 60 ))
while :; do
    status="$(docker inspect --format '{{.State.Health.Status}}' "$name")"
    if [[ "$status" == healthy ]]; then
        echo "PASS: container healthy"
        break
    fi
    if [[ "$status" == unhealthy || $(date +%s) -ge $deadline ]]; then
        echo "FAIL: container health ($status)" >&2
        docker logs "$name" >&2
        exit 1
    fi
    sleep 1
done

python3 - "$port" <<'PY'
import json
import sys
from urllib.request import Request, urlopen

port = sys.argv[1]
base = f"http://127.0.0.1:{port}"

def request(path, method="GET", data=None):
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Host": "localhost"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    with urlopen(Request(base + path, data=body, headers=headers, method=method), timeout=5) as response:
        assert response.status == 200, response.status
        return response.read().decode()

assert json.loads(request("/api/health")) == {"status": "ok"}
print("PASS: GET /api/health (Host: localhost)")
assert "<html" in request("/").lower()
print("PASS: GET / returns HTML")
assert json.loads(request("/api/settings/preferences", "PUT", {"digest_language": "zh-Hans"})) == {
    "digest_language": "zh-Hans", "youtube_captions": False, "youtube_skip_shorts": True
}
print("PASS: saved zh-Hans preference")
PY

test "$(docker exec "$name" id -u)" != 0
echo "PASS: process is non-root"
docker exec "$name" test -f /data/catchup.sqlite3
echo "PASS: database exists on volume"
docker exec "$name" test ! -e /app/.env
docker exec "$name" test ! -e /app/backend
echo "PASS: image excludes .env and backend source tree"
docker restart "$name" >/dev/null
deadline=$(( $(date +%s) + 60 ))
while [[ "$(docker inspect --format '{{.State.Health.Status}}' "$name")" != healthy ]]; do
    if [[ $(date +%s) -ge $deadline ]]; then
        echo "FAIL: container not healthy after restart" >&2
        exit 1
    fi
    sleep 1
done
python3 - "$port" <<'PY'
import json
import sys
from urllib.request import Request, urlopen

request = Request(
    f"http://127.0.0.1:{sys.argv[1]}/api/settings/preferences",
    headers={"Host": "localhost"},
)
with urlopen(request, timeout=5) as response:
    assert response.status == 200
    assert json.load(response) == {
        "digest_language": "zh-Hans", "youtube_captions": False, "youtube_skip_shorts": True
    }
print("PASS: preference survives restart")
PY
