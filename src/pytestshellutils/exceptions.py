# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Pytest Shell Utilities related exceptions.
"""
from typing import Optional

from pytestshellutils.utils.processes import ProcessResult


class ShellUtilsException(Exception):
    """
    Base pytest shell utilities exception.
    """


class CallbackException(ShellUtilsException):
    """
    Exception raised during a before/after start/stop daemon callback.
    """


class ProcessFailed(ShellUtilsException):
    """
    Exception raised when a sub-process fails.

    Arguments:
        message:
            The exception message

    Keyword Arguments:
        process_result:
            The ``ProcessResult`` instance when the exception occurred
    """

    def __init__(self, message: str, process_result: Optional[ProcessResult] = None) -> None:
        super().__init__()
        self.message = message
        self.process_result = process_result

    def __str__(self) -> str:
        """
        Return a printable representation of the exception.
        """
        message = self.message
        if self.process_result:
            if not message.endswith("\n"):
                message += "\n"
            message += str(self.process_result)
        return message


class FactoryFailure(ProcessFailed):
    """
    Exception raised when a sub-process fails on one of the factories.
    """


class FactoryNotStarted(FactoryFailure):
    """
    Exception raised when a factory failed to start.

    Please look at :py:class:`~pytestshellutils.exceptions.FactoryFailure` for the supported keyword
    arguments documentation.
    """


class FactoryNotRunning(FactoryFailure):
    """
    Exception raised when trying to use a factory's `.stopped` context manager and the factory is not running.

    Please look at :py:class:`~pytestshellutils.exceptions.FactoryFailure` for the supported keyword
    arguments documentation.
    """


class ProcessNotStarted(FactoryFailure):
    """
    Exception raised when a process failed to start.

    Please look at :py:class:`~pytestshellutils.exceptions.FactoryFailure` for the supported keywords.
    arguments documentation.
    """


class FactoryTimeout(FactoryNotStarted):
    """
    Exception raised when a process timed-out.

    Please look at :py:class:`~pytestshellutils.exceptions.FactoryFailure` for the supported keywords.
    arguments documentation.
    """
