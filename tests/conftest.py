# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import functools
import logging
import os
import stat
import tempfile
import textwrap
from typing import Optional
from typing import Tuple

import pytest

try:
    from pytest import FixtureRequest
except ImportError:
    from _pytest.fixtures import FixtureRequest

try:  # pragma: no cover
    import importlib.metadata

    pkg_version = importlib.metadata.version
except ImportError:  # pragma: no cover
    try:
        import importlib_metadata

        pkg_version = importlib_metadata.version
    except ImportError:  # pragma: no cover
        import pkg_resources

        def pkg_version(package):  # type: ignore[no-untyped-def]
            return pkg_resources.get_distribution(package).version


log = logging.getLogger(__name__)


def pkg_version_info(package: str) -> Tuple[int, ...]:
    """
    Return a version info tuple for the given package.
    """
    return tuple(int(part) for part in pkg_version(package).split(".") if part.isdigit())


if pkg_version_info("pytest") >= (6, 2):
    pytest_plugins = ["pytester"]
else:  # pragma: no cover

    @pytest.fixture
    def pytester() -> None:
        pytest.skip("The pytester fixture is not available in Pytest < 6.2.0")


class Tempfiles:
    """
    Class which generates temporary files and cleans them when done.
    """

    def __init__(self, request: FixtureRequest):
        self.request = request

    def makepyfile(
        self, contents: str, prefix: Optional[str] = None, executable: bool = False
    ) -> str:
        """
        Creates a python file and returns it's path.
        """
        tfile = tempfile.NamedTemporaryFile("w", prefix=prefix or "tmp", suffix=".py", delete=False)
        contents = textwrap.dedent(contents.lstrip("\n")).strip()
        tfile.write(contents)
        tfile.close()
        if executable is True:
            st = os.stat(tfile.name)
            os.chmod(tfile.name, st.st_mode | stat.S_IEXEC)
        self.request.addfinalizer(functools.partial(self._delete_temp_file, tfile.name))
        with open(tfile.name, encoding="utf-8") as rfh:
            log.debug(
                "Created python file with contents:\n>>>>> %s >>>>>\n%s\n<<<<< %s <<<<<\n",
                tfile.name,
                rfh.read(),
                tfile.name,
            )
        return tfile.name

    def _delete_temp_file(self, fpath: str) -> None:
        """
        Cleanup the temporary path.
        """
        if os.path.exists(fpath):  # pragma: no branch
            os.unlink(fpath)


@pytest.fixture
def tempfiles(request: FixtureRequest) -> Tempfiles:
    """
    Temporary files fixture.
    """
    return Tempfiles(request)
