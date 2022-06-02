# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test ``pytestshellutils.utils.processes.ProcessResult``.
"""
import json as jsonlib
import textwrap

import pytest
from pytest_subtests import SubTests

from pytestshellutils.utils.processes import ProcessResult


@pytest.mark.parametrize("returncode", [None, 1.0, -1.0, "0"])
def test_non_int_returncode_raises_exception(returncode: int) -> None:
    with pytest.raises(ValueError):
        ProcessResult(returncode=returncode, stdout="", stderr="")


def test_attributes(subtests: SubTests) -> None:
    returncode = 0
    stdout = "STDOUT"
    stderr = "STDERR"
    cmdline = None
    data = None

    with subtests.test(returncode=returncode, stdout=stdout, stderr=stderr):
        ret = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)
        assert ret.returncode == returncode
        assert ret.stdout == stdout
        assert ret.stderr == stderr
        assert ret.data == data
        assert ret.cmdline == cmdline

    cmdline = ["1", "2", "3"]
    with subtests.test(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline):
        ret = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline)
        assert ret.returncode == returncode
        assert ret.stdout == stdout
        assert ret.stderr == stderr
        assert ret.data == data
        assert ret.cmdline == cmdline

    data = {"ret": {"a": 1}}
    stdout = jsonlib.dumps(data)
    with subtests.test(
        returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline, data=data
    ):
        ret = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline)
        assert ret.returncode == returncode
        assert ret.stdout == stdout
        assert ret.stderr == stderr
        assert ret.data == data
        assert ret.cmdline == cmdline

    data_key = "ret"
    with subtests.test(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        cmdline=cmdline,
        data=data,
        data_key=data_key,
    ):
        ret = ProcessResult(
            returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline, data_key="ret"
        )
        assert ret.returncode == returncode
        assert ret.stdout == stdout
        assert ret.stderr == stderr
        assert ret.data == data[data_key]
        assert ret.cmdline == cmdline


def test_str_formatting(subtests: SubTests) -> None:
    returncode = 0
    stdout = "STDOUT"
    stderr = "STDERR"
    cmdline = None
    data = {"ret": {"a": 1}}
    data_key = None

    with subtests.test(returncode=returncode, stdout=stdout, stderr=stderr):
        ret = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)
        expected = textwrap.dedent(
            """\
            ProcessResult
             Returncode: {}
             Process Output:
               >>>>> STDOUT >>>>>
            {}
               <<<<< STDOUT <<<<<
               >>>>> STDERR >>>>>
            {}
               <<<<< STDERR <<<<<
        """.format(
                returncode, stdout, stderr
            )
        )
        assert str(ret) == expected

    cmdline = ["1", "2", "3"]
    with subtests.test(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline):
        ret = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline)
        expected = textwrap.dedent(
            """\
            ProcessResult
             Command Line: {!r}
             Returncode: {}
             Process Output:
               >>>>> STDOUT >>>>>
            {}
               <<<<< STDOUT <<<<<
               >>>>> STDERR >>>>>
            {}
               <<<<< STDERR <<<<<
        """.format(
                cmdline,
                returncode,
                stdout,
                stderr,
            )
        )
        assert str(ret) == expected

    stdout = jsonlib.dumps(data)
    with subtests.test(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline):
        ret = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline)
        expected = textwrap.dedent(
            """\
            ProcessResult
             Command Line: {!r}
             Returncode: {}
             Process Output:
               >>>>> STDOUT >>>>>
            {}
               <<<<< STDOUT <<<<<
               >>>>> STDERR >>>>>
            {}
               <<<<< STDERR <<<<<
             Parsed JSON Data:
               {!r}
        """.format(
                cmdline, returncode, stdout, stderr, data
            )
        )
        assert str(ret) == expected

    data_key = "ret"
    with subtests.test(
        returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline, data_key=data_key
    ):
        ret = ProcessResult(
            returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline, data_key=data_key
        )
        expected = textwrap.dedent(
            """\
            ProcessResult
             Command Line: {!r}
             Returncode: {}
             Process Output:
               >>>>> STDOUT >>>>>
            {}
               <<<<< STDOUT <<<<<
               >>>>> STDERR >>>>>
            {}
               <<<<< STDERR <<<<<
             Parsed JSON Data:
               {!r}
        """.format(
                cmdline, returncode, stdout, stderr, data[data_key]
            )
        )
        assert str(ret) == expected
