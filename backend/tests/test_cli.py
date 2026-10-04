from unittest.mock import Mock

import pytest

from catchup import cli


def test_serve_help(capsys) -> None:
    with pytest.raises(SystemExit) as result:
        cli.main(["serve", "--help"])
    assert result.value.code == 0
    assert "--host" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("arguments", "host", "port"),
    [(["serve"], "127.0.0.1", 8000), (["serve", "--host", "0.0.0.0", "--port", "9000"], "0.0.0.0", 9000)],
)
def test_serve_calls_uvicorn(monkeypatch, arguments, host, port) -> None:
    app = object()
    run = Mock()
    monkeypatch.setattr(cli, "create_app", lambda: app)
    monkeypatch.setattr(cli.uvicorn, "run", run)
    cli.main(arguments)
    run.assert_called_once_with(app, host=host, port=port)
