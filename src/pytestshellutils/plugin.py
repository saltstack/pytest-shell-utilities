# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""
Pytest shell utilities plugin.
"""
import pytest

from pytestshellutils.shell import Subprocess


@pytest.fixture  # type: ignore[misc]
def shell() -> Subprocess:
    """
    Shell fixture.
    """
    return Subprocess()
