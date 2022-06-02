# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""
Pytest shell utilities plugin.
"""
from __future__ import generator_stop
import pytest
from pytestshellutils.shell import Subprocess


@pytest.fixture
def shell() -> Subprocess:
    """
    Shell fixture.

    Example:
        .. code-block:: python

           def test_assert_good_exitcode(shell):

               ret = shell.run("exit", "0")
               assert ret.returncode == 0


           def test_assert_bad_exitcode(shell):

               ret = shell.run("exit", "1")
               assert ret.returncode == 1
    """
    return Subprocess()
