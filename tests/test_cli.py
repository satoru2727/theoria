from typer.testing import CliRunner

from theoria.cli import app


def test_app_exists() -> None:
    assert app is not None


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "theoria" in result.stdout
