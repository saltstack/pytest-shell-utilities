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
def process_result():
    return ProcessResult(returncode=0, stdout=MARY_HAD_A_LITTLE_LAMB, stderr=None)


def test_instance_types():
    ret = ProcessResult(returncode=0, stdout="STDOUT", stderr="STDERR")
    assert isinstance(ret.stdout, str)
    assert isinstance(ret.stderr, str)


def test_matcher_attribute(process_result):
    process_result.stdout.matcher.fnmatch_lines_random(
        [
            "*had a little*",
            "Its fleece was white*",
            "*Mary went",
            "The lamb was sure to go.",
        ]
    )
