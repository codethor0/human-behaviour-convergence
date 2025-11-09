import json

import pytest

from hbc import cli


def test_cli_forecast_basic(capsys):
    exit_code = cli.main(
        [
            "--region",
            "us-midwest",
            "--horizon",
            "7",
            "--modalities",
            "satellite",
            "mobility",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["region"] == "us-midwest"
    assert data["horizon"] == 7
    assert data["modalities"] == ["satellite", "mobility"]
    assert data["ethics"] == {"synthetic": True, "pii": False}
    # Deterministic repeat
    exit_code_repeat = cli.main(
        [
            "--region",
            "us-midwest",
            "--horizon",
            "7",
            "--modalities",
            "satellite",
            "mobility",
            "--json",
        ]
    )
    assert exit_code_repeat == 0
    compact_out = capsys.readouterr().out.strip()
    assert compact_out.startswith("{") and "\n" not in compact_out
    assert json.loads(compact_out) == data


def test_cli_invalid_horizon():
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--region", "us-west", "--horizon", "0"])
    assert excinfo.value.code == 2
