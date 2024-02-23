# Copyright 2022-2024 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import pathlib
import sys
import tempfile

import pytest

from pytestshellutils.shell import Subprocess
from tests.conftest import Tempfiles


def test_run_call(tempfiles: Tempfiles, shell: Subprocess) -> None:
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import os
        import json
        print(json.dumps(dict(**os.environ)), flush=True)
        exit(0)
        """
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 0


def test_run_cwd(tempfiles: Tempfiles, shell: Subprocess) -> None:
    system_tempdir = str(pathlib.Path(tempfile.gettempdir()).resolve())
    assert str(shell.cwd.resolve()) != system_tempdir
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import pathlib
        print(str(pathlib.Path.cwd().resolve()), flush=True)
        exit(0)
        """
    )
    result = shell.run(sys.executable, script, cwd=system_tempdir)
    assert result.returncode == 0
    assert result.stdout.strip() == system_tempdir


def test_run_shell(shell: Subprocess) -> None:
    with pytest.raises(FileNotFoundError):
        shell.run("exit", "0")
    with pytest.raises(FileNotFoundError):
        shell.run("exit", "0", shell=False)
    result = shell.run("exit", "0", shell=True)
    assert result.returncode == 0
