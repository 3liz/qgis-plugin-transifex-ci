"""
Parameters management.
"""

import shutil
import tomllib

from configparser import ConfigParser
from functools import cached_property
from pathlib import Path
from typing import (
    Optional,
    Sequence,
)

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    HttpUrl,
)

from . import logger


def _parse_str_sequence(value: Sequence[str] | str) -> Sequence[str]:
    if isinstance(value, str):
        # Parse comma separated list
        value = value.split(",") if value else ()
    return value


class Parameters(BaseModel, extra="forbid"):
    rootdir: Path = Field(title="Root directory")

    plugin_source: Path = Field(
        title="Plugin source",
        description="The directory of the source code in the repository",
    )
    organization: str = Field(
        title="The organization slug",
        description="""
        The organization slug on translation platform (e.g. Transifex).
        """,
    )
    project: str = Field(
        title="Transifex Project",
        description="""
        The project's name on Transifex.
        Usually this is the same as the Github's project slug.
        """
    )
    resource: str = Field(
        title="Transifex resource",
        description="he resource name in transifex. Default to project's name.",
    )
    source_lang: str = Field(
        default="en",
        title="Source language",
        description="""
        """,
    )
    lrelease_executable: FilePath = Field(
        default=Path(shutil.which("lrelease") or "lrelease"),
        validate_default=True,
        title="lrelease executable"
    )
    pylupdate5_executable: FilePath = Field(
        default=Path(shutil.which("pylupdate5") or "pylupdate5"),
        validate_default=True,
        title="pylupdate5 executable",
    )
    repository_url: HttpUrl = Field(
        title="Repository url",
        description="The source repository url",
    )
    selected_languages: Sequence[str] = Field(
        default=(),
        title="Languages",
        description="""
        A list of selected languages to pick from availables languages
        """,
    )
    minimum_translation: Optional[float] = Field(
        default=None,
        title="Minimum translation",
        description="""
        Minimum translation ratio required for a language.
        If the translation ratio is below that value, the langage
        be discarded.
        """,
        ge=0.0,
        le=100.0,
    )

    @cached_property
    def plugin_path(self) -> Path:
        return self.rootdir.joinpath(self.plugin_source)


def find_config_file(rootdir: Path) -> Optional[Path]:
    """Find candidate config file"""
    for file in (
        "pyproject.toml",
        "qgis-transifex-ci.toml",
        ".qgis-transifex-ci.toml",
    ):
        p = rootdir.joinpath(file)
        if p.exists():
            return p
    else:
        return None


def read_config_from_file(path: Path) -> dict:
    """Read bare configuration from file"""
    with path.open("rb") as fh:
        config = tomllib.load(fh)
        logger.debug("== Read config from %s", path)
        if path.stem == "pyproject":
            config = config.get("tool", {})
        return config.get("qgis-transifex-ci", {})


def load_parameters(rootdir: Optional[Path] = None) -> Parameters:
    """Load parameters from config files"""
    rootdir = rootdir or Path.cwd()
    path = find_config_file(rootdir)
    if not path:
        raise FileNotFoundError("Cannot find configuration file")
    config = read_config_from_file(path) if path else {}
    config.update(rootdir=rootdir)

    # Check resource - default to project
    if not config.get("resource"):
        config["resource"] = config.get("project")

    plugin_source = config["plugin_source"]

    if not config.get("repository_url"):
        # Get the repository from metadata
        metadata = ConfigParser()
        metadata.optionxform = str  # type: ignore [assignment]
        metadata.read(rootdir.joinpath(plugin_source, "metadata.txt"))
        config["repository_url"] = metadata.get("general", "repository")

    return Parameters.model_validate(config)
