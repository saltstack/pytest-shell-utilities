# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Process related utilities.
"""
from __future__ import generator_stop
import errno
import json
import logging
import pprint
import signal
import weakref
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import attr
import psutil

try:
    from pytest import LineMatcher
except ImportError:
    from _pytest.pytester import LineMatcher
from pytestshellutils.utils import warn_until

log = logging.getLogger(__name__)


class MatchString(str):
    """
    Simple subclass around ``str`` which provides a ``.matcher`` property.

    This ``.matcher`` property is an instance of :py:class:`~pytest.LineMatcher`
    """

    @property
    def matcher(self) -> LineMatcher:
        """
        Return an instance of :py:class:`~pytest.LineMatcher`.
        """
        return LineMatcher(self.splitlines())


def convert_string_to_match_string(value: Optional[str]) -> Optional[MatchString]:
    """
    Convert strings into ``MatchString`` instances.
    """
    if isinstance(value, str):
        return MatchString(value)
    return value


@attr.s(frozen=True, kw_only=True)
class ProcessResult:
    """
    Wrapper class around a subprocess result.

    This class serves the purpose of having a common result class which will hold the
    resulting data from a subprocess command.

    Keyword Arguments:
        returncode:
            The returncode returned by the process
        stdout:
            The ``stdout`` returned by the process
        stderr:
            The ``stderr`` returned by the process
        cmdline:
            The command line used to start the process
        data:
            The data returned by parsing ``stdout``, when possible.
        data_key:
            When ``stdout`` can be parsed as JSON, sometimes there's a top level key which is not
            that interesting. By using ``data_key``, we define that we're actually only interested
            on the data structure which is keyed by ``data_key``.

    Note:
        Cast :py:class:`~pytestshellutils.utils.processes.ProcessResult` to a string to pretty-print it.
    """

    returncode = attr.ib()
    stdout = attr.ib(converter=convert_string_to_match_string)
    stderr = attr.ib(converter=convert_string_to_match_string)
    cmdline = attr.ib(default=None)
    data_key = attr.ib(default=None)
    data = attr.ib()

    @returncode.validator
    def _validate_returncode(self, attribute: Any, value: int) -> None:
        """
        Validate the value type.
        """
        if not isinstance(value, int):
            raise ValueError(
                "'returncode' needs to be an integer, not '{0}'".format(type(value))
            )

    @data.default
    def _default_data(self) -> Optional[Dict[Any, Any]]:
        """
        Try to parse the passed ``stdout`` as JSON as the default data value.
        """
        stdout = self.stdout.strip() if self.stdout else None
        if stdout:
            try:
                data = json.loads(stdout.strip())
                if data and self.data_key and self.data_key in data:
                    data = data[self.data_key]
                return data
            except ValueError:
                pass
        return None

    @property
    def exitcode(self) -> int:
        """
        Return the process returncode.

        This property is deprecated and should not be used.
        It only exists to support projects that are migrating from
        pytest-salt-factories versions. Use ``.returncode`` instead.
        """
        warn_until(
            '2.0.0',
            "The '.exitcode' property is deprecated and will cease to exist after pytest-shell-utilities {version}. Please use '.returncode' instead.",
        )
        return self.returncode

    @property
    def json(self) -> Optional[Dict[Any, Any]]:
        """
        Return the process output parsed as JSON, if possible.

        This property is deprecated and should not be used.
        It only exists to support projects that are migrating from
        pytest-salt-factories versions. Use ``.data`` instead.
        """
        warn_until(
            '2.0.0',
            "The '.json' property is deprecated and will cease to exist after pytest-shell-utilities {version}. Please use '.data' instead.",
        )
        return self.data

    def __str__(self) -> str:
        """
        String representation of the class.
        """
        message = self.__class__.__name__
        if self.cmdline:
            message += '\n Command Line: {0}'.format(self.cmdline)
        if self.returncode is not None:
            message += '\n Returncode: {0}'.format(self.returncode)
        if self.stdout and self.stdout.strip() or self.stderr and self.stderr.strip():
            message += '\n Process Output:'
        if self.stdout and self.stdout.strip():
            message += '\n   >>>>> STDOUT >>>>>\n{0}\n   <<<<< STDOUT <<<<<'.format(
                self.stdout
            )
        if self.stderr and self.stderr.strip():
            message += '\n   >>>>> STDERR >>>>>\n{0}\n   <<<<< STDERR <<<<<'.format(
                self.stderr
            )
        if self.data:
            message += '\n Parsed JSON Data:\n'
            message += '\n'.join(
                '   {0}'.format(line) for line in pprint.pformat(self.data).splitlines()
            )
        return message + '\n'


def collect_child_processes(pid: int) -> List[psutil.Process]:
    """
    Try to collect any started child processes of the provided pid.

    Arguments:
        pid:
            The PID of the process

    Returns:
        List of child processes
    """
    children = None
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    return children


def _get_cmdline(proc: psutil.Process) -> Optional[Any]:
    try:
        return proc._cmdline
    except AttributeError:
        try:
            cmdline = proc.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cmdline = None
        except OSError:
            cmdline = None
        except RuntimeError:
            cmdline = None
        if not cmdline:
            try:
                cmdline = proc.as_dict()
            except psutil.NoSuchProcess:
                cmdline = '<could not be retrived; dead process: {0}>'.format(proc)
            except (psutil.AccessDenied, OSError):
                cmdline = weakref.proxy(proc)
        proc._cmdline = cmdline
    return proc._cmdline


def _terminate_process_list(
    process_list: List[psutil.Process], kill: bool = False, slow_stop: bool = False
) -> None:
    log.info(
        'Terminating process list:\n%s',
        pprint.pformat([_get_cmdline(proc) for proc in process_list]),
    )
    for process in process_list[:]:
        if not psutil.pid_exists(process.pid):
            process_list.remove(process)
            continue
        try:
            if not kill and process.status() == psutil.STATUS_ZOMBIE:
                continue
            if kill:
                log.info('Killing process(%s): %s', process.pid, _get_cmdline(process))
                process.kill()
            else:
                log.info(
                    'Terminating process(%s): %s', process.pid, _get_cmdline(process)
                )
                try:
                    if slow_stop:
                        process.send_signal(signal.SIGTERM)
                        try:
                            process.wait(2)
                        except psutil.TimeoutExpired:
                            if psutil.pid_exists(process.pid):
                                continue
                    else:
                        process.terminate()
                except OSError as exc:
                    if exc.errno not in (errno.ESRCH, errno.EACCES):
                        raise
            if not psutil.pid_exists(process.pid):
                process_list.remove(process)
        except psutil.NoSuchProcess:
            process_list.remove(process)


def terminate_process_list(
    process_list: List[psutil.Process], kill: bool = False, slow_stop: bool = False
) -> None:
    """
    Terminate a list of processes.

    Arguments:
        process_list:
            An iterable of :py:class:`psutil.Process` instances to terminate

    Keyword Arguments:
        kill:
            Kill the process instead of terminating it.
        slow_stop:
            First try to terminate each process in the list, and if termination was not successful, kill it.

    Returns:
        Nothing.
    """

    def on_process_terminated(proc: psutil.Process) -> None:
        log.info(
            'Process %s terminated with exit code: %s',
            getattr(proc, '_cmdline', proc),
            proc.returncode,
        )

    log.info(
        'Terminating process list. 1st step. kill: %s, slow stop: %s', kill, slow_stop
    )
    seen_pids = []
    start_count = len(process_list)
    for proc in process_list[:]:
        if proc.pid in seen_pids:
            process_list.remove(proc)
        seen_pids.append(proc.pid)
    end_count = len(process_list)
    if end_count < start_count:
        log.debug(
            'Removed %d duplicates from the initial process list',
            start_count - end_count,
        )
    _terminate_process_list(process_list, kill=kill, slow_stop=slow_stop)
    psutil.wait_procs(process_list, timeout=5, callback=on_process_terminated)
    if process_list:
        log.info(
            'Terminating process list. 2nd step. kill: %s, slow stop: %s',
            slow_stop is False,
            slow_stop,
        )
        _terminate_process_list(
            process_list, kill=slow_stop is False, slow_stop=slow_stop
        )
        psutil.wait_procs(process_list, timeout=5, callback=on_process_terminated)
    if process_list:
        log.info('Terminating process list. 3rd step. kill: True, slow stop: False')
        _terminate_process_list(process_list, kill=True, slow_stop=False)
        psutil.wait_procs(process_list, timeout=5, callback=on_process_terminated)
    if process_list:
        log.warning('Some processes failed to properly terminate: %s', process_list)


def terminate_process(
    pid: Optional[int] = None,
    process: Optional[psutil.Process] = None,
    children: Optional[List[psutil.Process]] = None,
    kill_children: Optional[bool] = None,
    slow_stop: bool = False,
) -> None:
    """
    Try to terminate/kill the started process.

    Keyword Arguments:
        pid:
            The PID of the process
        process:
            An instance of :py:class:`psutil.Process`
        children:
            An iterable of :py:class:`psutil.Process` instances, children to the process being terminated
        kill_children:
            Also try to terminate/kill child processes
        slow_stop:
            First try to terminate each process in the list, and if termination was not successful, kill it.
    """
    children = children or []
    process_list = []
    if kill_children is None:
        kill_children = True if slow_stop is False else kill_children
    if pid and not process:
        try:
            process = psutil.Process(pid)
            process_list.append(process)
        except psutil.NoSuchProcess:
            process = None
    if kill_children:
        if process:
            children.extend(collect_child_processes(process.pid))
        if children:
            process_list.extend(children)
    if process_list:
        if process:
            log.info(
                'Stopping process %s and respective children: %s', process, children
            )
        else:
            log.info('Terminating process list: %s', process_list)
        terminate_process_list(
            process_list, kill=slow_stop is False, slow_stop=slow_stop
        )
