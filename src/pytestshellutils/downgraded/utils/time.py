# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
# pylint: disable=wildcard-import,unused-wildcard-import
"""
Namespace the standard library :py:mod:`time` module.

This module's sole purpose is to have the standard library :py:mod:`time` module functions under a different
namespace to be used in pytest-shell-utilities so that projects using it, which need to mock :py:mod:`time` functions,
don't influence the pytest-shell-utilities run time behavior.
"""
from __future__ import generator_stop
from time import *
