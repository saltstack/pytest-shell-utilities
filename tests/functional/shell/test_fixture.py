# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import sys

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
