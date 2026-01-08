
from pathlib import Path
from typing import (
    Iterator,
    Optional,
)

import requests
import transifex.api as tx

from transifex.api import transifex_api as tx_api
from transifex.api.jsonapi.exceptions import DoesNotExist

from .errors import TranslationError


class Resource:
    def __init__(self, res: tx.Resource):
        self._res = res

    def upload(self, resource_path: Path):
        tx_api.ResourceStringsAsyncUpload.upload(
            resource_path.read_text(),
            resource=self._res,
        )

    def download(
        self,
        lang: str,
        output_path: Path,
    ):
        """Fetch the translation resource matching the given language"""
        language = tx_api.Language.get(code=lang)

        url = tx_api.ResourceTranslationsAsyncDownload.download(
            resource=self._res, language=language
        )

        r = requests.get(url)
        # Transifex returns None encoding and the apparent_encoding is Windows-1254
        # what leads to malformed result strings.
        # So we set the encoding hardcoded to utf-8.
        if not r.encoding:
            r.encoding = "utf-8"

        translated_content = r.text
        output_path.write_text(translated_content)

    def update(self, path: Path):
        """Update resource with 'path' content"""
        tx_api.ResourceStringsAsyncUpload.upload(
            path.read_text(),
            resource=self._res,
        )


class Project:
    def __init__(self, project: tx.Project):
        self._proj = project

    def resource(self, name: str) -> Optional[Resource]:
        try:
            return Resource(self._proj.fetch("resources").get(slug=name))
        except DoesNotExist:
            return None

    def create_resource(self, name: str) -> Resource:
        return Resource(
            tx_api.Resource.create(
                project=self._proj,
                name=name,
                slug=name,
                i18n_format=tx_api.I18nFormat(id="QT"),
            ),
        )

    def resources(self) -> Iterator[Resource]:
        return (Resource(res) for res in self._proj.fetch("resources").all())

    def languages(self) -> Iterator[tx.Language]:
        return self._proj.fetch("languages").all()

    def language_stats(self, resource: str) -> Iterator[tuple[str, int, float]]:
        """Return the language statistics based on the number of translated strings"""
        try:
            res = self._proj.fetch("resources").get(slug=resource)
        except DoesNotExist:
            return

        for st in tx_api.ResourceLanguageStats.filter(project=self._proj, resource=res):
            _ , _, code = st.id.partition(":l:")
            if st.total_strings > 0:
                ratio = 100.0 * (st.translated_strings / st.total_strings)
            else:
                ratio = 0.
            yield (code, st.total_strings, ratio)

    def add_languages(self, *languages: str):
        self._proj.add(
            "languages",
            [lang for code in languages if (lang := tx_api.Language.get(code=code))]
        )


class Client:
    def __init__(self, org: str, token: str):
        tx_api.setup(auth=token)
        try:
            self._org = tx_api.Organization.get(slug=org)
        except DoesNotExist:
            raise TranslationError(f"The organization '{org}' is no registered")

    def project(self, name: str) -> Optional[Project]:
        try:
            return Project(self._org.fetch("projects").get(slug=name))
        except DoesNotExist:
            return None

    def create_project(
        self,
        name: str,
        lang: str,
        *,
        private: bool = False,
        repository_url: Optional[str] = None,
    ) -> Project:
        kwargs = {
            "name": name,
            "slug": name,
            "source_language": tx_api.Language.get(code=lang),
            "private": private,
            "organization": self._org,
        }

        if repository_url:
            kwargs["repository_url"] = repository_url
        elif not private:
            raise TranslationError("A repository url is required for public projects")

        return Project(tx_api.Project.create(**kwargs))
