import os
import shutil
import tempfile
from contextlib import contextmanager

import importlib.metadata as metadata

from scrapyd import Config
from scrapyd.exceptions import BadEggError
from scrapyd.utils import initialize_component


def activate_egg(eggpath):
    """Activate a Scrapy egg file. This is meant to be used from egg runners
    to activate a Scrapy egg file. Don't use it from other code as it may
    leave unwanted side effects.
    """
    try:
        distributions = metadata.distributions(path=[eggpath])
        distribution = next(distributions, None)
        if not distribution:
            raise BadEggError

        distribution.activate()

        # Ensure SCRAPY_SETTINGS_MODULE is set
        entry_info = distribution.entry_points.select(group="scrapy", name="settings")
        if entry_info:
            os.environ.setdefault("SCRAPY_SETTINGS_MODULE", entry_info[0].value)
    except Exception as e:
        raise BadEggError from e

@contextmanager
def project_environment(project):
    config = Config()
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")

    eggversion = os.environ.get("SCRAPYD_EGG_VERSION", None)
    sanitized_version, egg = eggstorage.get(project, eggversion)
    os.environ.setdefault('SCRAPYD_EGG_VERSION', sanitized_version)
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
