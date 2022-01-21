# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
import textwrap

import pytest

import pytestshellutils.exceptions as exceptions
from pytestshellutils.utils.processes import ProcessResult


def test_process_failed_message():
    message = "The message"
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message)
    assert str(exc.value) == message


def test_process_failed_cmdline():
    message = "The message"
    cmdline = ["python", "--version"]
    expected = textwrap.dedent(
        """\
        {}
        ProcessResult
         Command Line: {!r}
         Returncode: 0
    """.format(
            message, cmdline
        )
    )
    pres = ProcessResult(returncode=0, cmdline=cmdline, stdout="", stderr="")
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected


def test_process_failed_returncode():
    message = "The message"
    returncode = 1
    expected = textwrap.dedent(
        """\
        {}
        ProcessResult
         Returncode: {}
    """.format(
            message, returncode
        )
    )
    pres = ProcessResult(returncode=returncode, stdout="", stderr="")
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected


def test_process_failed_stdout():
    message = "The message"
    stdout = "This is the STDOUT"
    expected = textwrap.dedent(
        """\
        {}
        ProcessResult
         Returncode: 0
         Process Output:
           >>>>> STDOUT >>>>>
        {}
           <<<<< STDOUT <<<<<
    """.format(
            message, stdout
        )
    )
    pres = ProcessResult(returncode=0, stdout=stdout, stderr="")
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected


def test_process_failed_stderr():
    message = "The message"
    stderr = "This is the STDERR"
    expected = textwrap.dedent(
        """\
        {}
        ProcessResult
         Returncode: 0
         Process Output:
           >>>>> STDERR >>>>>
        {}
           <<<<< STDERR <<<<<
    """.format(
            message, stderr
        )
    )
    pres = ProcessResult(returncode=0, stdout="", stderr=stderr)
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected


def test_process_failed_stdout_and_stderr():
    message = "The message"
    stdout = "This is the STDOUT"
    stderr = "This is the STDERR"
    expected = textwrap.dedent(
        """\
        {}
        ProcessResult
         Returncode: 0
         Process Output:
           >>>>> STDOUT >>>>>
        {}
           <<<<< STDOUT <<<<<
           >>>>> STDERR >>>>>
        {}
           <<<<< STDERR <<<<<
    """.format(
            message, stdout, stderr
        )
    )
    pres = ProcessResult(returncode=0, stdout=stdout, stderr=stderr)
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected


def test_process_failed_cmdline_stdout_and_stderr():
    message = "The message"
    stdout = "This is the STDOUT"
    stderr = "This is the STDERR"
    cmdline = ["python", "--version"]
    expected = textwrap.dedent(
        """\
        {}
        ProcessResult
         Command Line: {!r}
         Returncode: 0
         Process Output:
           >>>>> STDOUT >>>>>
        {}
           <<<<< STDOUT <<<<<
           >>>>> STDERR >>>>>
        {}
           <<<<< STDERR <<<<<
    """.format(
            message, cmdline, stdout, stderr
        )
    )
    pres = ProcessResult(returncode=0, stdout=stdout, stderr=stderr, cmdline=cmdline)
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected


def test_process_failed_cmdline_stdout_stderr_and_returncode():
    message = "The message"
    stdout = "This is the STDOUT"
    stderr = "This is the STDERR"
    cmdline = ["python", "--version"]
    returncode = 1
    expected = textwrap.dedent(
        """\
        {}
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
            message, cmdline, returncode, stdout, stderr
        )
    )
    pres = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr, cmdline=cmdline)
    with pytest.raises(exceptions.FactoryFailure) as exc:
        raise exceptions.FactoryFailure(message, process_result=pres)
    output = str(exc.value)
    assert output == expected
