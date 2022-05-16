# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import os
import sys
from typing import cast
from unittest import mock

import pytest

from pytestshellutils.customtypes import EnvironDict
from pytestshellutils.exceptions import FactoryTimeout
from pytestshellutils.shell import Subprocess


@pytest.mark.parametrize("exitcode", [0, 1, 3, 9, 40, 120])
def test_exitcode(exitcode, tempfiles):
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


def test_timeout_defined_on_class_instantiation(tempfiles):
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


def test_timeout_defined_run(tempfiles):
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
def test_json_output(input_str, expected_object, tempfiles):
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


def test_stderr_output(tempfiles):
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


def test_unicode_output(tempfiles):
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


def test_process_failed_to_start(tempfiles):
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


def test_environ(tempfiles):
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


def test_env_in_run_call(tempfiles):
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


def test_not_started():
    shell = Subprocess()
    assert shell.is_running() is False
    assert not shell.pid
    assert shell.terminate() is None


def test_display_name(tempfiles):
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


def test_glibc_race_condition_handling(tempfiles):
    shell = Subprocess()
    stderr = "Inconsistency detected by ld.so ... _dl_allocate_tls_init\n"
    script = tempfiles.makepyfile(
        """
        # coding=utf-8
        import sys
        import time
        print("{}", file=sys.stderr, flush=True)
        time.sleep(0.1)
        exit(127)
        """.format(
            stderr.strip()
        )
    )
    with mock.patch("pytestshellutils.shell.glibc_prone_to_race_condition", return_value=False):
        ret = shell.run(sys.executable, script)
        assert ret.returncode == 127
        assert ret.stderr == stderr
    with mock.patch("pytestshellutils.shell.glibc_prone_to_race_condition", return_value=True):
        with pytest.raises(pytest.skip.Exception):
            shell.run(sys.executable, script)
