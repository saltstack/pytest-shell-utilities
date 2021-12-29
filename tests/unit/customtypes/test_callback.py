# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import pytest

from pytestshellutils.customtypes import Callback


def foo_func(arg1, arg2, keyword_argument=None):
    return {"arg1": arg1, "arg2": arg2, "keyword_argument": keyword_argument}


@pytest.fixture
def callback():
    return Callback(func=foo_func, args=("a1", "a2"), kwargs={"keyword_argument": True})


def test___str__(callback):
    assert str(callback) == "foo_func('a1', 'a2', keyword_argument=True)"


def test___call__(callback):
    assert callback() == {"arg1": "a1", "arg2": "a2", "keyword_argument": True}
