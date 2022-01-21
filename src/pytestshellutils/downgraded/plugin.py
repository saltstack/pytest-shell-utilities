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
    """
    return Subprocess()
