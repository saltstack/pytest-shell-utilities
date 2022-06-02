# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import generator_stop
import inspect
import pathlib
import sys
import warnings
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TYPE_CHECKING
from typing import Union
import packaging.version
import pytestshellutils

if TYPE_CHECKING:
    from packaging.version import Version


def resolved_pathlib_path(path: Union[str, pathlib.Path]) -> pathlib.Path:
    """
    Return a resolved ``pathlib.Path``.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    return path.resolve()


def format_callback_to_string(
    callback: Union[str, Callable[..., Any]],
    args: Optional[Tuple[Any, ...]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Convert a callback, its arguments and keyword arguments to a string suitable for logging purposes.

    Arguments:
        callback:
            The callback function

    Keyword Arguments:
        args:
            The callback arguments
        kwargs:
            The callback keyword arguments

    Returns:
        str: The formatted callback string
    """
    callback_str = None
    if not isinstance(callback, str):
        try:
            callback_str = '{0}('.format(callback.__qualname__)
        except AttributeError:
            callback_str = '{0}('.format(callback.__name__)
    else:
        callback_str = '{0}('.format(callback)
    if args:
        callback_str += ', '.join([repr(arg) for arg in args])
    if kwargs:
        if args:
            callback_str += ', '
        callback_str += ', '.join(['{0}={1}'.format(k, v) for k, v in kwargs.items()])
    callback_str += ')'
    return callback_str


def warn_until(
    version: str,
    message: str,
    category: Type[Warning] = DeprecationWarning,
    stacklevel: Optional[int] = None,
    _dont_call_warnings: bool = False,
    _pkg_version_: Optional[str] = None,
) -> None:
    """
    Show a deprecation warning.

    Helper function to raise a warning, by default, a ``DeprecationWarning``,
    until the provided ``version``, after which, a ``RuntimeError`` will
    be raised to remind the developers to remove the warning because the
    target version has been reached.

    Arguments:
        version:
            The version string after which the warning becomes a ``RuntimeError``.
            For example ``2.1``.
        message:
            The warning message to be displayed.

    Keyword Arguments:
        category:
            The warning class to be thrown, by default ``DeprecationWarning``
        stacklevel:
            There should be no need to set the value of ``stacklevel``.
        _dont_call_warnings:
            This parameter is used just to get the functionality until the actual
            error is to be issued. When we're only after the version checks to
            raise a ``RuntimeError``.

    Returns:
        Nothing.
    """
    _version = packaging.version.parse(version)
    if _pkg_version_ is None:
        _pkg_version_ = pytestshellutils.__version__
    _pkg_version = packaging.version.parse(_pkg_version_)
    if stacklevel is None:
        stacklevel = 3
    if _pkg_version >= _version:
        caller = inspect.getframeinfo(sys._getframe(stacklevel - 1))
        raise RuntimeError(
            "The warning triggered on filename '{filename}', line number {lineno}, is supposed to be shown until version {until_version} is released. Current version is now {version}. Please remove the warning.".format(
                filename=caller.filename,
                lineno=caller.lineno,
                until_version=_pkg_version_,
                version=version,
            )
        )
    if _dont_call_warnings is False:
        warnings.warn(message.format(version=version), category, stacklevel=stacklevel)
