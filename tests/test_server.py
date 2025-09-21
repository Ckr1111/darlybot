import json
import time
import urllib.request

import pytest

from darlybot.input_controller import SimulatedInputController
from darlybot.navigator import SongNavigator
from darlybot.server import SongServer
from darlybot.song_index import SongIndex


@pytest.fixture()
def sample_server(tmp_path):
    csv_path = tmp_path / "곡순서.csv"
    csv_path.write_text(
        "title_number,title\n0001,Alpha\n0002,Beta\n0003,Bolt\n",
        encoding="utf-8",
    )
    index = SongIndex(csv_path)
    controller = SimulatedInputController()
    navigator = SongNavigator(index, controller)
    server = SongServer(navigator, index=index, host="127.0.0.1", port=0)
    server.start()
    # Allow the background thread to bind before the test continues.
    time.sleep(0.1)
    yield server, controller
    server.stop()


def _request_json(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, body) as response:
            return json.loads(response.read().decode("utf-8"))
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def test_ping_endpoint(sample_server):
    server, _ = sample_server
    payload = _request_json(f"http://{server.host}:{server.port}/ping")
    assert payload == {"status": "ok"}


def test_navigate_endpoint_sends_keys(sample_server):
    server, controller = sample_server
    payload = _request_json(
        f"http://{server.host}:{server.port}/navigate",
        method="POST",
        data={"title_number": "0002"},
    )
    assert payload["title"] == "Beta"
    assert payload["keys"] == ["b"]
    assert controller.sent_keys == ["b"]
