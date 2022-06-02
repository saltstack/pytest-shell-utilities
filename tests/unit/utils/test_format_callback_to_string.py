# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
from pytestshellutils.utils import format_callback_to_string


def test_format_from_string() -> None:
    func = "the_function"
    args = ("one", "two")
    kwargs = {"three": 3}
    assert (
        format_callback_to_string(func, args=args, kwargs=kwargs)
        == "the_function('one', 'two', three=3)"
    )


def test_format_just_args() -> None:
    func = "the_function"
    args = ("one", "two")
    assert format_callback_to_string(func, args=args) == "the_function('one', 'two')"


def test_format_just_kwargs() -> None:
    func = "the_function"
    kwargs = {"three": 3}
    assert format_callback_to_string(func, kwargs=kwargs) == "the_function(three=3)"


def test_format_no_args_nor_kwargs() -> None:
    func = "the_function"
    assert format_callback_to_string(func) == "the_function()"


def test_format_from_function() -> None:
    func = format_callback_to_string
    args = ("one", "two")
    kwargs = {"three": 3}
    assert (
        format_callback_to_string(func, args, kwargs)
        == "format_callback_to_string('one', 'two', three=3)"
    )
