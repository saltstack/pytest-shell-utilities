# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
# type: ignore
import importlib
import pathlib
import re
import sys


USE_DOWNGRADED_TRANSPILED_CODE = sys.version_info < (3, 7)


if USE_DOWNGRADED_TRANSPILED_CODE:
    # We generated downgraded code just for Py3.5
    # Let's just import from those modules instead

    class NoTypingImporter:
        """
        Meta importer to redirect imports on Py<3.7.
        """

        NO_REDIRECT_NAMES = (
            "pytestshellutils.version",
            "pytestshellutils.downgraded",
        )

        def find_module(self, module_name, package_path=None):  # noqa: D102
            if module_name.startswith(self.NO_REDIRECT_NAMES):
                return None
            if not module_name.startswith("pytestshellutils"):
                return None
            return self

        def load_module(self, name):  # noqa: D102
            if not name.startswith(self.NO_REDIRECT_NAMES):
                mod = importlib.import_module("pytestshellutils.downgraded.{}".format(name[17:]))
            else:
                mod = importlib.import_module(name)
            sys.modules[name] = mod
            return mod

    # Try our importer first
    sys.meta_path = [NoTypingImporter()] + sys.meta_path


try:
    from .version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.not-installed"
    try:
        from importlib.metadata import version, PackageNotFoundError

        try:
            __version__ = version("pytest-shell-utilities")
        except PackageNotFoundError:
            # package is not installed
            pass
    except ImportError:
        try:
            from importlib_metadata import version, PackageNotFoundError

            try:
                __version__ = version("pytest-shell-utilities")
            except PackageNotFoundError:
                # package is not installed
                pass
        except ImportError:
            try:
                from pkg_resources import get_distribution, DistributionNotFound

                try:
                    __version__ = get_distribution("pytest-shell-utilities").version
                except DistributionNotFound:
                    # package is not installed
                    pass
            except ImportError:
                # pkg resources isn't even available?!
                pass


# Define __version_info__ attribute
VERSION_INFO_REGEX = re.compile(
    r"(?P<major>[\d]+)\.(?P<minor>[\d]+)\.(?P<patch>[\d]+)"
    r"(?:\.dev(?P<commits>[\d]+)\+g(?P<sha>[a-z0-9]+)\.d(?P<date>[\d]+))?"
)
try:  # pragma: no branch
    __version_info__ = tuple(
        int(p) if p.isdigit() else p for p in VERSION_INFO_REGEX.match(__version__).groups() if p
    )
except AttributeError:  # pragma: no cover
    __version_info__ = (-1, -1, -1)
finally:
    del VERSION_INFO_REGEX


# Define some constants
CODE_ROOT_DIR = pathlib.Path(__file__).resolve().parent
IS_WINDOWS = sys.platform.startswith("win")
IS_DARWIN = IS_OSX = sys.platform.startswith("darwin")
