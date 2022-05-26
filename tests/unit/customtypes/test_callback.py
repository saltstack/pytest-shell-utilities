# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import pytest

from pytestshellutils.customtypes import Callback


def func(*args, **kwargs):
    return {"args": args, "kwargs": kwargs}


@pytest.fixture
def callback():
    return Callback(func=func, args=("a1", "a2"), kwargs={"keyword_argument": True})


def test___str__(callback):
    assert str(callback) == "func('a1', 'a2', keyword_argument=True)"


def test___call__(callback):
    assert callback() == {"args": ("a1", "a2"), "kwargs": {"keyword_argument": True}}


def test___call__extra_args(callback):
    assert callback("bar") == {"args": ("bar", "a1", "a2"), "kwargs": {"keyword_argument": True}}


def test___call__extra_kwargs(callback):
    assert callback(bar=2) == {"args": ("a1", "a2"), "kwargs": {"keyword_argument": True, "bar": 2}}


def test___call__override_kwarg(callback):
    assert callback(keyword_argument=False) == {
        "args": ("a1", "a2"),
        "kwargs": {"keyword_argument": False},
    }
