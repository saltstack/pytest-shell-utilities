# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import os
import sys
from typing import Any
from typing import cast

import pytest

from pytestshellutils.customtypes import EnvironDict
from pytestshellutils.exceptions import FactoryTimeout
from pytestshellutils.shell import Subprocess
from tests.conftest import Tempfiles


@pytest.mark.parametrize("exitcode", [0, 1, 3, 9, 40, 120])
def test_exitcode(exitcode: int, tempfiles: Tempfiles) -> None:
    shell = Subprocess()
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import time
        time.sleep(0.125)
        exit({})
        """.format(
            exitcode
        )
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == exitcode


def test_timeout_defined_on_class_instantiation(tempfiles: Tempfiles) -> None:
    shell = Subprocess(timeout=0.5)
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import time
        time.sleep(1)
        exit(0)
        """
    )
    with pytest.raises(FactoryTimeout):
        shell.run(sys.executable, script)


def test_timeout_defined_run(tempfiles: Tempfiles) -> None:
    shell = Subprocess()
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import time
        time.sleep(0.5)
        exit(0)
        """
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 0

    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import time
        time.sleep(0.5)
        exit(0)
        """
    )
    with pytest.raises(FactoryTimeout):
        shell.run(sys.executable, script, _timeout=0.1)


@pytest.mark.parametrize(
    "input_str,expected_object",
    [
        # Good JSON
        ('{"a": "a", "1": 1}', {"a": "a", "1": 1}),
        # Bad JSON
        ("{'a': 'a', '1': 1}", None),
    ],
)
def test_json_output(input_str: str, expected_object: Any, tempfiles: Tempfiles) -> None:
    shell = Subprocess()
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import sys
        sys.stdout.write('''{}''')
        exit(0)
        """.format(
            input_str
        )
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 0
    if expected_object:
        assert result.data == expected_object
    assert result.stdout == input_str


def test_stderr_output(tempfiles: Tempfiles) -> None:
    input_str = "Thou shalt not exit cleanly"
    shell = Subprocess()
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        exit("{}")
        """.format(
            input_str
        )
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 1
    assert result.stderr == input_str + "\n"


def test_unicode_output(tempfiles: Tempfiles) -> None:
    shell = Subprocess()
    script = tempfiles.makepyfile(
        r"""
        # coding=utf-8
        from __future__ import print_function
        import sys
        sys.stdout.write(u'STDOUT F\xe1tima')
        sys.stdout.flush()
        sys.stderr.write(u'STDERR F\xe1tima')
        sys.stderr.flush()
        exit(0)
        """
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 0, str(result)
    assert result.stdout == "STDOUT Fátima"
    assert result.stderr == "STDERR Fátima"


def test_process_failed_to_start(tempfiles: Tempfiles) -> None:
    shell = Subprocess()
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        1/0
        """
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 1
    assert "ZeroDivisionError: division by zero" in result.stderr


def test_environ(tempfiles: Tempfiles) -> None:
    environ = cast(EnvironDict, os.environ.copy())
    environ["FOO"] = "foo"
    shell = Subprocess(environ=environ)
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
    assert result.data
    assert "FOO" in result.data
    assert result.data["FOO"] == "foo"


def test_env_in_run_call(tempfiles: Tempfiles) -> None:
    env = cast(EnvironDict, {"FOO": "bar"})
    environ = cast(EnvironDict, os.environ.copy())
    environ["FOO"] = "foo"
    shell = Subprocess(environ=environ)
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import os
        import json
        print(json.dumps(dict(**os.environ)), flush=True)
        exit(0)
        """
    )
    result = shell.run(sys.executable, script, env=env)
    assert result.returncode == 0
    assert result.data
    assert "FOO" in result.data
    assert result.data["FOO"] == env["FOO"]


def test_not_started() -> None:
    shell = Subprocess()
    assert shell.is_running() is False
    assert not shell.pid
    assert shell.terminate() is None


def test_display_name(tempfiles: Tempfiles) -> None:
    shell = Subprocess()
    assert shell.get_display_name() == "Subprocess()"
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import time
        time.sleep(0.125)
        exit(0)
        """
    )
    result = shell.run(sys.executable, script)
    assert result.returncode == 0
    assert shell.get_display_name() == "Subprocess([{!r}, {!r}])".format(sys.executable, script)
