import sys

from typing import Sequence

import click

from . import logger
from .errors import TranslationError
from .translation import Translation


@click.group()
@click.version_option(
    package_name="qgis-plugin-package-ci",
    message="Qgis plugin ci: %(version)s",
)
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
def cli(verbose: int):
    match verbose:
        case 0:
            logger.setup(logger.LogLevel.WARNING)
        case 1:
            logger.setup(logger.LogLevel.INFO)
        case n if n > 1:
            logger.setup(logger.LogLevel.DEBUG)


#
# Changelog
#
class NoChangeLog(Exception):
    pass


@cli.command("push")
@click.option(
    "--transifex-token",
    help="Transifex API token",
    envvar="QGIS_TRANSIFEX_CI_TOKEN",
    required=True,
)
@click.option("--dry-run", is_flag=True, help="Dry run")
def make_push(transifex_token: str, dry_run: bool):
    """Push source translation file to Transifex"""
    from .parameters import load_parameters

    parameters = load_parameters()
    t = Translation(parameters, transifex_token)
    t.update_strings(parameters)
    if not dry_run:
        t.push()
    else:
        click.echo(click.style("Not pushing to transifex because it is a dry-run", fg="yellow"))


@cli.command("pull")
@click.option(
    "--transifex-token",
    help="Transifex API token",
    envvar="QGIS_TRANSIFEX_CI_TOKEN",
    required=True,
)
@click.option("--compile", is_flag=True, help="Compile TS files into QM files")
@click.option("--lang", "-l", multiple=True, help="Selected languages")
def make_pull(transifex_token: str, compile: bool, lang: Sequence[str]):
    """Pull translation from transifex"""
    from .parameters import load_parameters

    parameters = load_parameters()

    if not lang:
        lang = parameters.selected_languages

    t = Translation(parameters, transifex_token)
    t.pull(selected_languages=lang)
    if compile:
        Translation.compile_strings(parameters)


@cli.command("compile")
def make_compile():
    """Compile ts files"""
    from .parameters import load_parameters

    parameters = load_parameters()
    Translation.compile_strings(parameters)


@cli.command("list")
@click.option(
    "--transifex-token",
    help="Transifex API token",
    envvar="QGIS_TRANSIFEX_CI_TOKEN",
    required=True,
)
@click.option("--json", "json_format", is_flag=True, help="Output as json")
def list_languages(transifex_token: str, json_format: bool):
    """List availables translation"""
    from .client import Client
    from .parameters import load_parameters

    parameters = load_parameters()
    project = Client(parameters.organization, transifex_token).project(parameters.project)
    if not project:
        raise TranslationError(f"Project {parameters.project} not found")

    stats = {code: (strings, ratio) for (code, strings, ratio) in project.language_stats(parameters.resource)}
    languages = sorted(
        ((lang, stats[lang.code]) for lang in project.languages()),
        key=lambda n: n[1][1],
        reverse=True,
    )
    if json_format:
        import json
        click.echo(
            json.dumps(
                [{
                    "code": lang.code,
                    "name": lang.name,
                    "strings": stat[0],
                    "ratio": stat[1],
                } for lang, stat in languages],
                indent=4,
            ),
        )
    else:
        for i, (lang, stat) in enumerate(languages):
            click.echo(f"{i + 1:>3}. {lang.code:<10} {lang.name:<25} {stat[0]:<8} {stat[1]:.2f}")


def main():
    try:
        cli()
    except NoChangeLog:
        sys.exit(1)
    except TranslationError as err:
        click.echo(click.style(f"ERROR: {err}", fg="red"), err=True)
        sys.exit(1)
