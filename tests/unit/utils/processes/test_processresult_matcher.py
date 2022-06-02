# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test ``pytestshellutils.utils.processes.ProcessResult``.
"""
import pytest

from pytestshellutils.utils.processes import ProcessResult


MARY_HAD_A_LITTLE_LAMB = """\
Mary had a little lamb,
Its fleece was white as snow;
And everywhere that Mary went
The lamb was sure to go.
"""


@pytest.fixture
def process_result() -> ProcessResult:
    return ProcessResult(returncode=0, stdout=MARY_HAD_A_LITTLE_LAMB, stderr=None)


def test_instance_types() -> None:
    ret = ProcessResult(returncode=0, stdout="STDOUT", stderr="STDERR")
    assert isinstance(ret.stdout, str)
    assert isinstance(ret.stderr, str)
    ret = ProcessResult(returncode=0, stdout=None, stderr=None)
    assert ret.stdout is None
    assert ret.stderr is None
    ret = ProcessResult(returncode=0, stdout=1, stderr=2, data=None)
    assert ret.stdout == 1
    assert ret.stderr == 2


def test_matcher_attribute(process_result: ProcessResult) -> None:
    process_result.stdout.matcher.fnmatch_lines_random(
        [
            "*had a little*",
            "Its fleece was white*",
            "*Mary went",
            "The lamb was sure to go.",
        ]
    )
