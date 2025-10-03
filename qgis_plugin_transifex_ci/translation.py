import subprocess

from pathlib import Path
from typing import Sequence

from . import logger
from .client import Client
from .errors import TranslationError
from .parameters import Parameters


class Translation:

    @classmethod
    def translation_file_path(cls, parameters: Parameters) -> Path:
        return parameters.plugin_path.joinpath(
            "i18n",
            f"{parameters.resource}_{parameters.source_lang}.ts",
        )

    def __init__(
        self,
        parameters: Parameters,
        tx_api_token: str,
    ):
        # Get the translation source file

        resource_name = parameters.resource
        resource_lang = parameters.source_lang

        self._plugin_path = parameters.plugin_path
        self._projectname = parameters.project

        self._ts_name = resource_name
        self._ts_path = self.translation_file_path(parameters)

        self._client = Client(parameters.organization, tx_api_token)

        project = self._client.project(parameters.project)
        if not project:
            project = self._client.create_project(
                parameters.project,
                resource_lang,
            )

        self._project = project

    def pull(self, selected_languages: Sequence[str] = ()):
        """
        Pull TS files from Transifex
        """
        resource = self._project.resource(self._ts_name)
        if not resource:
            raise TranslationError(f"Resource {self._ts_name} does not exists")

        languages = set(self._project.languages())
        logger.info("%s languages found for '%s'", len(languages), resource)

        # Ensure that the directory exists
        i18n_dir = self._plugin_path.joinpath("i18n")
        i18n_dir.mkdir(parents=True, exist_ok=True)

        if selected_languages:
            languages.intersection_update(selected_languages)

        for lang in sorted(languages):
            ts_file = i18n_dir.joinpath(f"{self._ts_name}_{lang}.ts")
            logger.info(f"Downloading translation file: {ts_file}")
            resource.download(lang, ts_file)

    def push(self):
        resource = self._project.create_resource(self._ts_name)

        logger.info(f"Pushing resource: {self._ts_name} from '{self._ts_path}'")
        resource.update(self._ts_path)

    @classmethod
    def update_strings(cls, parameters: Parameters):
        """Update TS files from plugin source strings"""
        plugin_path = parameters.plugin_path

        sources_py = plugin_path.glob("**/*.py")
        sources_ui = plugin_path.glob("**/*.ui")

        project_file = parameters.plugin_path.joinpath(f"{parameters.project}.pro")

        ts_path = cls.translation_file_path(parameters)

        with project_file.open("w") as fh:
            py_sources = " ".join(str(p.relative_to(plugin_path)) for p in sources_py)
            ui_sources = " ".join(str(p.relative_to(plugin_path)) for p in sources_ui)
            fh.write("CODECFORTR = UTF-8\n")
            fh.write(f"SOURCES = {py_sources}\n")
            fh.write(f"FORMS = {ui_sources}\n")
            fh.write(
                f"TRANSLATIONS = {ts_path.relative_to(plugin_path)}\n"
            )

        cmd = [str(parameters.pylupdate5_executable), "-noobsolete", str(project_file)]

        logger.debug("Running command %s", cmd)
        subprocess.run(cmd, check=True, text=True)

    @classmethod
    def compile_strings(cls, parameters: Parameters):
        """
        Compile TS file into QM files
        """
        cmd = [
            str(parameters.lrelease_executable),
            *(str(p) for p in parameters.plugin_path.glob("i18n/*.ts")),
        ]
        logger.debug("Running command %s", cmd)
        subprocess.run(cmd, check=True, text=True)
