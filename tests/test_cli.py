import os

from contextlib import chdir
from pathlib import Path

import pytest

from click.testing import CliRunner

from qgis_plugin_transifex_ci.main import cli

# XXX Click and log-cli-level option raise error:
# See https://github.com/pallets/click/issues/824


@pytest.mark.skipif(not os.getenv("QGIS_TRANSIFEX_CI_TOKEN"), reason="No transifex token defined")
def test_cli_push(fixtures: Path):
    with chdir(fixtures):
        runner = CliRunner()
        result = runner.invoke(cli, ["-vv", "push", "--dry-run"])

        print("\n::test_cli_push::", result.output)

        assert result.exit_code == 0


@pytest.mark.skipif(not os.getenv("QGIS_TRANSIFEX_CI_TOKEN"), reason="No transifex token defined")
def test_cli_pull(fixtures: Path):
    with chdir(fixtures):
        runner = CliRunner()
        result = runner.invoke(cli, ["-vv", "pull"])

        print("\n::test_cli_pull::", result.output)

        assert result.exit_code == 0
