# Standard library imports
import os
import shutil
import tempfile
from contextlib import contextmanager

# Third-party imports
from importlib import metadata

# Local application imports
from scrapyd import Config
from scrapyd.exceptions import BadEggError
from scrapyd.utils import initialize_component


def raise_bad_egg_error():
    err_msg = "No valid distribution found in eggpath"
    raise BadEggError(err_msg)


def activate_egg(eggpath):
    """Activate a Scrapy egg file."""
    try:
        distributions = list(metadata.distributions(path=[eggpath]))
        if not distributions:
            raise_bad_egg_error()

        # Ensure SCRAPY_SETTINGS_MODULE is set
        os.environ["SCRAPY_SETTINGS_MODULE"] = "streamingscrapper.settings"
    except Exception as e:
        raise BadEggError from e


@contextmanager
def project_environment(project):
    config = Config()
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")

    eggversion = os.environ.get("SCRAPYD_EGG_VERSION", None)
    sanitized_version, egg = eggstorage.get(project, eggversion)

    # It is 'SCRAPYD_EGG_VERSION' since v1.4.0 https://scrapyd.readthedocs.io/en/stable/news.html#id15
    if sanitized_version:
        os.environ.setdefault("SCRAPYD_EGG_VERSION", sanitized_version)

    tmp = None
    if egg:
        try:
            if hasattr(egg, "name"):  # for example, FileIO
                activate_egg(egg.name)
            else:  # for example, BytesIO
                prefix = f"{project}-{sanitized_version}-"
                tmp = tempfile.NamedTemporaryFile(suffix=".egg", prefix=prefix, delete=False)
                shutil.copyfileobj(egg, tmp)
                tmp.close()
                activate_egg(tmp.name)
        finally:
            egg.close()
    try:
        yield
    finally:
        if tmp:
            os.remove(tmp.name)


def main():
    project = os.environ["SCRAPY_PROJECT"]
    with project_environment(project):
        from scrapy.cmdline import execute

        execute()


if __name__ == "__main__":
    main()
