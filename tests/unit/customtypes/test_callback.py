# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
from typing import Any
from typing import Dict

import pytest

from pytestshellutils.customtypes import Callback


def func(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"args": args, "kwargs": kwargs}


@pytest.fixture
def callback() -> Callback:
    return Callback(func=func, args=("a1", "a2"), kwargs={"keyword_argument": True})


def test___str__(callback: Callback) -> None:
    assert str(callback) == "func('a1', 'a2', keyword_argument=True)"


def test___call__(callback: Callback) -> None:
    assert callback() == {"args": ("a1", "a2"), "kwargs": {"keyword_argument": True}}


def test___call__extra_args(callback: Callback) -> None:
    assert callback("bar") == {"args": ("bar", "a1", "a2"), "kwargs": {"keyword_argument": True}}


def test___call__extra_kwargs(callback: Callback) -> None:
    assert callback(bar=2) == {"args": ("a1", "a2"), "kwargs": {"keyword_argument": True, "bar": 2}}


def test___call__override_kwarg(callback: Callback) -> None:
    assert callback(keyword_argument=False) == {
        "args": ("a1", "a2"),
        "kwargs": {"keyword_argument": False},
    }
