# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Shelling class implementations.
"""
from __future__ import generator_stop
import atexit
import contextlib
import json
import locale
import logging
import os
import pathlib
import shutil
import subprocess
import sys
from tempfile import SpooledTemporaryFile
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union
import attr
import psutil
from pytestskipmarkers.utils import platform
from pytestshellutils.customtypes import Callback
from pytestshellutils.customtypes import EnvironDict
from pytestshellutils.exceptions import CallbackException
from pytestshellutils.exceptions import FactoryNotRunning
from pytestshellutils.exceptions import FactoryNotStarted
from pytestshellutils.exceptions import FactoryTimeout
from pytestshellutils.exceptions import ShellUtilsException
from pytestshellutils.utils import format_callback_to_string
from pytestshellutils.utils import ports
from pytestshellutils.utils import resolved_pathlib_path
from pytestshellutils.utils import time
from pytestshellutils.utils.processes import ProcessResult
from pytestshellutils.utils.processes import terminate_process
from pytestshellutils.utils.processes import terminate_process_list

if TYPE_CHECKING:
    from typing import Type
    from pytestsysstats.plugin import StatsProcesses
log = logging.getLogger(__name__)


@attr.s(slots=True, kw_only=True)
class BaseFactory:
    """
    Base factory class.

    Keyword Arguments:
        cwd:
            The path to the desired working directory
        environ:
            A dictionary of ``key``, ``value`` pairs to add to the environment.
    """

    cwd = attr.ib(converter=resolved_pathlib_path)
    environ = attr.ib(repr=False)

    @cwd.default
    def _default_cwd(self) -> pathlib.Path:
        """
        Return the default cwd to use.
        """
        return pathlib.Path.cwd()

    @environ.default
    def _default_environ(self) -> EnvironDict:
        """
        Return the default ``os.environ`` to use.
        """
        return cast(EnvironDict, os.environ.copy())


@attr.s(slots=True, kw_only=True)
class SubprocessImpl:
    """
    Subprocess interaction implementation.

    Arguments:
        factory:
            The factory instance, either :py:class:`~pytestshellutils.shell.Subprocess` or
            a sub-class of it.
    """

    factory = attr.ib()
    _terminal = attr.ib(repr=False, init=False, default=None)
    _terminal_stdout = attr.ib(repr=False, init=False, default=None)
    _terminal_stderr = attr.ib(repr=False, init=False, default=None)
    _terminal_result = attr.ib(repr=False, init=False, default=None)
    _terminal_timeout = attr.ib(repr=False, init=False, default=None)
    _children = attr.ib(repr=False, init=False, factory=list)

    def cmdline(self, *args: str, **kwargs: Any) -> List[str]:
        """
        Construct a list of arguments to use when starting the subprocess.

        Arguments:
            args:
                Additional arguments to use when starting the subprocess

        By default, this method will just call it's factory's ``cmdline()``
        method, but can be overridden.
        """
        return self.factory.cmdline(*args)

    def init_terminal(
        self, cmdline: List[str], env: Optional[EnvironDict] = None
    ) -> 'subprocess.Popen[Any]':
        """
        Instantiate a terminal with the passed command line(``cmdline``) and return it.

        Additionally, it sets a reference to it in ``self._terminal`` and also collects
        an initial listing of child processes which will be used when terminating the
        terminal

        Arguments:
            cmdline:
                List of strings to pass as ``args`` to :py:class:`~subprocess.Popen`

        Keyword Arguments:
            environ:
                A dictionary of ``key``, ``value`` pairs to add to the
                :py:attr:`pytestshellutils.shell.Factory.environ`.

        Returns:
            A :py:class:`~subprocess.Popen` instance.
        """
        environ = self.factory.environ.copy()
        if env is not None:
            environ.update(env)
        self._terminal_stdout = SpooledTemporaryFile(512000, buffering=0)
        self._terminal_stderr = SpooledTemporaryFile(512000, buffering=0)
        close_fds = None
        if platform.is_windows():
            close_fds = False
        elif platform.is_freebsd() and sys.version_info < (3, 9):
            close_fds = False
        else:
            close_fds = True
        self._terminal = subprocess.Popen(
            cmdline,
            stdout=self._terminal_stdout,
            stderr=self._terminal_stderr,
            shell=False,
            cwd=str(self.factory.cwd),
            universal_newlines=True,
            close_fds=close_fds,
            env=environ,
            bufsize=0,
        )
        self._terminal_result = None
        try:
            self._terminal.wait(timeout=0.05)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(psutil.NoSuchProcess):
                for child in psutil.Process(self._terminal.pid).children(
                    recursive=True
                ):
                    if child not in self._children:
                        self._children.append(child)
            atexit.register(self.terminate)
        return self._terminal

    def is_running(self) -> bool:
        """
        Returns true if the sub-process is alive.

        Returns:
            Returns true if the sub-process is alive
        """
        if not self._terminal:
            return False
        return self._terminal.poll() is None

    def terminate(self) -> ProcessResult:
        """
        Terminate the started subprocess.
        """
        return self._terminate()

    def _terminate(self) -> ProcessResult:
        """
        This method actually terminates the started subprocess.
        """
        if self._terminal is None:
            if TYPE_CHECKING:
                assert self._terminal_result
            return self._terminal_result
        atexit.unregister(self.terminate)
        log.info('Stopping %s', self.factory)
        with contextlib.suppress(psutil.NoSuchProcess):
            for child in psutil.Process(self._terminal.pid).children(recursive=True):
                if child not in self._children:
                    self._children.append(child)
        with self._terminal:
            try:
                if self.factory.slow_stop:
                    self._terminal.terminate()
                else:
                    self._terminal.kill()
                try:
                    self._terminal.wait(10)
                except subprocess.TimeoutExpired:
                    pass
            except ProcessLookupError:
                pass
            terminate_process(
                pid=self._terminal.pid,
                kill_children=True,
                children=self._children,
                slow_stop=self.factory.slow_stop,
            )
            self._terminal.wait()
            self._terminal.poll()
            self._terminal.communicate()
            if TYPE_CHECKING:
                assert self._terminal_stdout
            self._terminal_stdout.flush()
            self._terminal_stdout.seek(0)
            _read_stdout = self._terminal_stdout.read()
            try:
                stdout = self._terminal._translate_newlines(
                    _read_stdout, self.factory.system_encoding, sys.stdout.errors
                )
            except TypeError:
                stdout = self._terminal._translate_newlines(
                    _read_stdout, self.factory.system_encoding
                )
            self._terminal_stdout.close()
            if TYPE_CHECKING:
                assert self._terminal_stderr
            self._terminal_stderr.flush()
            self._terminal_stderr.seek(0)
            _read_stderr = self._terminal_stderr.read()
            try:
                stderr = self._terminal._translate_newlines(
                    _read_stderr, self.factory.system_encoding, sys.stderr.errors
                )
            except TypeError:
                stderr = self._terminal._translate_newlines(
                    _read_stderr, self.factory.system_encoding
                )
            self._terminal_stderr.close()
        try:
            self._terminal_result = ProcessResult(
                returncode=self._terminal.returncode,
                stdout=stdout,
                stderr=stderr,
                cmdline=cast(List[str], self._terminal.args),
            )
            log.info('%s %s', self.factory.__class__.__name__, self._terminal_result)
            return self._terminal_result
        finally:
            self._terminal = None
            self._terminal_stdout = None
            self._terminal_stderr = None
            self._children = []

    @property
    def pid(self) -> Optional[int]:
        """
        The pid of the running process. None if not running.
        """
        if not self._terminal:
            return None
        return self._terminal.pid

    def run(
        self, *args: str, env: Optional[EnvironDict] = None, **kwargs: Any
    ) -> 'subprocess.Popen[Any]':
        """
        Run the given command synchronously.
        """
        cmdline = self.cmdline(*args, **kwargs)
        log.info(
            '%s is running %r in CWD: %s ...', self.factory, cmdline, self.factory.cwd
        )
        return self.init_terminal(cmdline, env=env)


@attr.s(slots=True, kw_only=True)
class Factory(BaseFactory):
    """
    Base shell factory class.

    Keyword Arguments:
        slow_stop:
            Whether to terminate the processes by sending a :py:attr:`SIGTERM` signal or by calling
            :py:meth:`~subprocess.Popen.terminate` on the sub-process.
            When code coverage is enabled, one will want `slow_stop` set to `True` so that coverage data
            can be written down to disk.
        system_encoding:
            The system encoding to use when decoding the subprocess output. Defaults to "utf-8".
        timeout:
            The default maximum amount of seconds that a script should run.
            This value can be overridden when calling :py:meth:`~pytestshellutils.shell.Process.run` through
            the ``_timeout`` keyword argument, and, in that case, the timeout value applied would be that
            of ``_timeout`` instead of ``self.timeout``.
    """

    slow_stop = attr.ib(default=True)
    system_encoding = attr.ib(repr=False)
    timeout = attr.ib()
    impl = attr.ib(repr=False, init=False)
    _cmdline = attr.ib(repr=False, init=False, default=None)

    @system_encoding.default
    def _default_system_encoding(self) -> str:
        return self._get_default_system_encoding()

    @timeout.default
    def _set_timeout(self) -> Optional[int]:
        return self._get_default_timeout()

    def _get_default_system_encoding(self) -> str:
        encoding = None
        if not platform.is_windows() and sys.stdin is not None:
            encoding = sys.stdin.encoding
        if not encoding:
            try:
                encoding = locale.getdefaultlocale()[-1]
            except ValueError:
                pass
            if not encoding:
                encoding = sys.getdefaultencoding()
            if not encoding:
                if platform.is_darwin():
                    encoding = 'utf-8'
                elif platform.is_windows():
                    encoding = 'mbcs'
                else:
                    encoding = 'ascii'
        if not encoding:
            encoding = 'utf-8'
        return encoding

    def _get_default_timeout(self) -> Optional[int]:
        return None

    def _get_impl_class(self) -> 'Type[SubprocessImpl]':
        """
        Return the ``impl`` class to use.
        """
        return SubprocessImpl

    def __attrs_post_init__(self) -> None:
        """
        Post ``attrs`` class initialization routines.
        """
        impl_class = self._get_impl_class()
        self.impl = impl_class(factory=self)

    def cmdline(self, *args: str) -> List[str]:
        """
        Method to construct a command line.
        """
        self._cmdline = list(args)
        return self._cmdline

    def get_display_name(self) -> str:
        """
        Returns a human readable name for the factory.
        """
        return '{}({})'.format(self.__class__.__name__, self._cmdline or '')

    def is_running(self) -> bool:
        """
        Returns true if the sub-process is alive.
        """
        return self.impl.is_running()

    def terminate(self) -> ProcessResult:
        """
        Terminate the started subprocess.
        """
        return self.impl.terminate()

    @property
    def pid(self) -> Optional[int]:
        """
        The pid of the running process. None if not running.
        """
        return self.impl.pid


@attr.s(slots=True, kw_only=True)
class Subprocess(Factory):
    """
    Base shell factory class.
    """

    def run(
        self,
        *args: str,
        env: Optional[EnvironDict] = None,
        _timeout: Optional[Union[int, float]] = None,
        **kwargs: Any
    ) -> ProcessResult:
        """
        Run the given command synchronously.

        Keyword Arguments:
            args:
                The list of arguments to pass to :py:meth:`~pytestshellutils.shell.Subprocess.cmdline`
                to construct the command to run
            env:
                Pass a dictionary of environment key, value pairs to inject into the subprocess.
            _timeout:
                The timeout value for this particular ``run()`` call. If this value is not ``None``,
                it will be used instead of :py:attr:`~pytestshellutils.shell.Subprocess.timeout`,
                the default timeout.
        """
        start_time = time.time()
        self.impl._terminal_timeout = _timeout or self.timeout
        timmed_out = False
        try:
            self.impl.run(*args, env=env, **kwargs)
            if TYPE_CHECKING:
                assert self.impl._terminal
            self.impl._terminal.communicate(timeout=self.impl._terminal_timeout)
        except subprocess.TimeoutExpired:
            timmed_out = True
        result = self.terminate()
        cmdline = result.cmdline
        returncode = result.returncode
        if timmed_out:
            raise FactoryTimeout(
                '{} Failed to run: {}; Error: Timed out after {:.2f} seconds!'.format(
                    self, cmdline, time.time() - start_time
                ),
                process_result=result,
            )
        stdout, stderr, json_out = self.process_output(
            result.stdout, result.stderr, cmdline=cmdline
        )
        log.info(
            '%s completed %r in CWD: %s after %.2f seconds',
            self,
            cmdline,
            self.cwd,
            time.time() - start_time,
        )
        return ProcessResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            data=json_out,
            cmdline=cmdline,
        )

    def process_output(
        self, stdout: str, stderr: str, cmdline: Optional[List[str]] = None
    ) -> Tuple[str, str, Optional[Dict[Any, Any]]]:
        """
        Process the output. When possible JSON is loaded from the output.

        Returns:
            Returns a tuple in the form of ``(stdout, stderr, loaded_json)``
        """
        if stdout:
            try:
                json_out = json.loads(stdout)
            except ValueError:
                log.debug(
                    '%s failed to load JSON from the following output:\n%r',
                    self,
                    stdout,
                )
                json_out = None
        else:
            json_out = None
        return stdout, stderr, json_out


@attr.s(slots=True, kw_only=True)
class ScriptSubprocess(Subprocess):
    """
    Base CLI script/binary class.

    Keyword Arguments:
        script_name:
            This is the string containing the name of the binary to call on the subprocess, either the
            full path to it, or the basename. In case of the basename, the directory containing the
            basename must be in your ``$PATH`` variable.
        base_script_args:
            An list or tuple iterable of the base arguments to use when building the command line to
            launch the process

    Please look at :py:class:`~pytestshellutils.shell.Factory` for the additional supported keyword
    arguments documentation.
    """

    script_name = attr.ib()
    base_script_args = attr.ib(factory=list)

    def get_display_name(self) -> str:
        """
        Returns a human readable name for the factory.
        """
        return '{0}({1})'.format(
            self.__class__.__name__, pathlib.Path(self.script_name).name
        )

    def get_script_path(self) -> str:
        """
        Returns the path to the script to run.
        """
        script_path = None
        if os.path.isabs(self.script_name):
            script_path = self.script_name
        else:
            script_path = shutil.which(self.script_name)
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(
                "The CLI script '{0}' does not exist".format(self.script_name)
            )
        if TYPE_CHECKING:
            assert script_path
        return script_path

    def get_base_script_args(self) -> List[str]:
        """
        Returns any additional arguments to pass to the CLI script.
        """
        return list(self.base_script_args)

    def get_script_args(self) -> List[str]:
        """
        Returns any additional arguments to pass to the CLI script.
        """
        return []

    def cmdline(self, *args: str) -> List[str]:
        """
        Construct a list of arguments to use when starting the subprocess.

        Arguments:
            args:
                Additional arguments to use when starting the subprocess
        """
        return (
            [self.get_script_path()]
            + self.get_base_script_args()
            + self.get_script_args()
            + list(args)
        )


@attr.s(kw_only=True, slots=True, frozen=True)
class StartDaemonCallArguments:
    """
    This class holds the arguments and keyword arguments used to start a daemon.

    It's used when restarting the daemon so that the same call is used.

    Keyword Arguments:
        args:
            List of arguments
        kwargs:
            Dictionary of keyword arguments
    """

    args = attr.ib()
    kwargs = attr.ib()


@attr.s(slots=True, kw_only=True)
class DaemonImpl(SubprocessImpl):
    """
    Daemon subprocess interaction implementation.

    Please look at :py:class:`~pytestshellutils.shell.SubprocessImpl` for the additional supported keyword
    arguments documentation.
    """

    factory = attr.ib()
    _before_start_callbacks = attr.ib(repr=False, hash=False, factory=list)
    _after_start_callbacks = attr.ib(repr=False, hash=False, factory=list)
    _before_terminate_callbacks = attr.ib(repr=False, hash=False, factory=list)
    _after_terminate_callbacks = attr.ib(repr=False, hash=False, factory=list)
    _start_args_and_kwargs = attr.ib(init=False, repr=False, hash=False, default=None)

    def before_start(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run before the daemon starts.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self._before_start_callbacks.append(
            Callback(func=callback, args=args, kwargs=kwargs)
        )

    def after_start(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run after the daemon starts.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self._after_start_callbacks.append(
            Callback(func=callback, args=args, kwargs=kwargs)
        )

    def before_terminate(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run before the daemon terminates.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self._before_terminate_callbacks.append(
            Callback(func=callback, args=args, kwargs=kwargs)
        )

    def after_terminate(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run after the daemon terminates.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self._after_terminate_callbacks.append(
            Callback(func=callback, args=args, kwargs=kwargs)
        )

    def start(
        self,
        *extra_cli_arguments: str,
        max_start_attempts: Optional[int] = None,
        start_timeout: Optional[Union[int, float]] = None
    ) -> bool:
        """
        Start the daemon.

        Keyword Arguments:
            extra_cli_arguments:
                Extra arguments to pass to the CLI that starts the daemon
            max_start_attempts:
                Maximum number of attempts to try and start the daemon in case of failures
            start_timeout:
                The maximum number of seconds to wait before considering that the daemon did not start

        Returns:
            bool: A boolean indicating if the start was successful or not.
        """
        if self.is_running():
            log.warning('%s is already running.', self)
            return True
        self._start_args_and_kwargs = StartDaemonCallArguments(
            args=extra_cli_arguments,
            kwargs={
                'max_start_attempts': max_start_attempts,
                'start_timeout': start_timeout,
            },
        )
        process_running = False
        start_time = time.time()
        start_attempts = max_start_attempts or self.factory.max_start_attempts
        current_attempt = 0
        run_arguments = list(extra_cli_arguments)
        while True:
            if process_running:
                break
            current_attempt += 1
            if current_attempt > start_attempts:
                break
            log.info(
                'Starting %s. Attempt: %d of %d',
                self.factory,
                current_attempt,
                start_attempts,
            )
            for callback in self._before_start_callbacks:
                try:
                    callback()
                except CallbackException as exc:
                    log.info(
                        'Exception raised when running %s: %s',
                        callback,
                        exc,
                        exc_info=True,
                    )
            current_start_time = time.time()
            start_running_timeout = current_start_time + (
                start_timeout or self.factory.start_timeout
            )
            if (
                current_attempt > 1
                and self.factory.extra_cli_arguments_after_first_start_failure
            ):
                run_arguments = list(extra_cli_arguments) + list(
                    self.factory.extra_cli_arguments_after_first_start_failure
                )
            self.run(*run_arguments)
            if not self.is_running():
                time.sleep(0.5)
            while time.time() <= start_running_timeout:
                if not self.is_running():
                    log.warning('%s is no longer running', self.factory)
                    self.terminate()
                    break
                try:
                    if (
                        self.factory.run_start_checks(
                            current_start_time, start_running_timeout
                        )
                        is False
                    ):
                        time.sleep(1)
                        continue
                except FactoryNotStarted:
                    self.terminate()
                    break
                log.info(
                    'The %s factory is running after %d attempts. Took %1.2f seconds',
                    self.factory,
                    current_attempt,
                    time.time() - start_time,
                )
                process_running = True
                break
            else:
                self.terminate()
        if process_running:
            for callback in self._after_start_callbacks:
                try:
                    callback()
                except CallbackException as exc:
                    log.info(
                        'Exception raised when running %s: %s',
                        callback,
                        exc,
                        exc_info=True,
                    )
            return process_running
        result = self.terminate()
        raise FactoryNotStarted(
            'The {} factory has failed to confirm running status after {} attempts, which took {:.2f} seconds'.format(
                self.factory, current_attempt - 1, time.time() - start_time
            ),
            process_result=result,
        )

    def terminate(self) -> ProcessResult:
        """
        Terminate the daemon.
        """
        if self._terminal_result is not None:
            return self._terminal_result
        for callback in self._before_terminate_callbacks:
            try:
                callback()
            except CallbackException as exc:
                log.info(
                    'Exception raised when running %s: %s', callback, exc, exc_info=True
                )
        try:
            return super().terminate()
        finally:
            for callback in self._after_terminate_callbacks:
                try:
                    callback()
                except CallbackException as exc:
                    log.warning(
                        'Exception raised when running %s: %s',
                        callback,
                        exc,
                        exc_info=True,
                    )

    def get_start_arguments(self) -> StartDaemonCallArguments:
        """
        Return the arguments and keyword arguments used when starting the daemon.
        """
        return self._start_args_and_kwargs


@attr.s(slots=True, kw_only=True)
class Daemon(ScriptSubprocess):
    """
    Base daemon factory.

    Keyword Arguments:
        check_ports:
            List of ports to try and connect to while confirming that the daemon is up and running
        extra_cli_arguments_after_first_start_failure:
            Extra arguments to pass to the CLI that starts the daemon after the first failure
        max_start_attempts:
            Maximum number of attempts to try and start the daemon in case of failures
        start_timeout:
            The maximum number of seconds to wait before considering that the daemon did not start

    Please look at :py:class:`~pytestshellutils.shell.Subprocess` for the additional supported keyword
    arguments documentation.
    """

    impl = attr.ib(repr=False, init=False)
    script_name = attr.ib()
    base_script_args = attr.ib(factory=list)
    check_ports = attr.ib(factory=list)
    stats_processes = attr.ib(repr=False, hash=False, default=None)
    start_timeout = attr.ib(repr=False)
    max_start_attempts = attr.ib(repr=False, default=3)
    extra_cli_arguments_after_first_start_failure = attr.ib(hash=False, factory=list)
    listen_ports = attr.ib(init=False, repr=False, hash=False, factory=list)
    _start_checks_callbacks = attr.ib(repr=False, hash=False, factory=list)

    def _get_impl_class(self) -> 'Type[DaemonImpl]':
        """
        Return the ``impl`` class to use.
        """
        return DaemonImpl

    def __attrs_post_init__(self) -> None:
        """
        Post ``attrs`` class initialization routines.
        """
        super().__attrs_post_init__()
        if self.check_ports and not isinstance(self.check_ports, (list, tuple)):
            self.check_ports = [self.check_ports]
        if self.check_ports:
            self.listen_ports.extend(self.check_ports)
        self.after_start(self._add_factory_to_stats_processes)
        self.after_terminate(self._terminate_processes_matching_listen_ports)
        self.after_terminate(self._remove_factory_from_stats_processes)
        self.start_check(self._check_listening_ports)

    def before_start(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run before the daemon starts.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self.impl.before_start(callback, *args, **kwargs)

    def after_start(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run after the daemon starts.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self.impl.after_start(callback, *args, **kwargs)

    def before_terminate(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run before the daemon terminates.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self.impl.before_terminate(callback, *args, **kwargs)

    def after_terminate(
        self, callback: Callable[[], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function callback to run after the daemon terminates.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.
        """
        self.impl.after_terminate(callback, *args, **kwargs)

    def start_check(
        self, callback: Callable[..., bool], *args: Any, **kwargs: Any
    ) -> None:
        """
        Register a function to run after the daemon starts to confirm readiness for work.

        The callback must accept as the first argument ``timeout_at`` which is a float.
        The callback must stop trying to confirm running behavior once ``time.time() > timeout_at``.
        The callback should return ``True`` to confirm that the daemon is ready for work.

        Arguments:
            callback:
                The function to call back

        Keyword Arguments:
            args:
                The arguments to pass to the callback
            kwargs:
                The keyword arguments to pass to the callback

        Returns:
            Nothing.

        Example:
            .. code-block:: python

                def check_running_state(timeout_at: float) -> bool:
                    while time.time() <= timeout_at:
                        # run some checks
                        ...
                        # if all is good
                        break
                    else:
                        return False
                    return True
        """
        self._start_checks_callbacks.append(
            Callback(func=callback, args=args, kwargs=kwargs)
        )

    def get_check_ports(self) -> List[int]:
        """
        Return a list of ports to check against to ensure the daemon is running.
        """
        return self.check_ports or []

    def get_start_check_callbacks(self) -> List[Callback]:
        """
        Return a list of the start check callbacks.
        """
        return self._start_checks_callbacks or []

    def start(
        self,
        *extra_cli_arguments: str,
        max_start_attempts: Optional[int] = None,
        start_timeout: Optional[Union[int, float]] = None
    ) -> bool:
        """
        Start the daemon.
        """
        return self.impl.start(
            *extra_cli_arguments,
            max_start_attempts=max_start_attempts,
            start_timeout=start_timeout,
        )

    @contextlib.contextmanager
    def started(
        self,
        *extra_cli_arguments: str,
        max_start_attempts: Optional[int] = None,
        start_timeout: Optional[Union[int, float]] = None
    ) -> Generator['Daemon', None, None]:
        """
        Start the daemon and return it's instance so it can be used as a context manager.
        """
        try:
            self.start(
                *extra_cli_arguments,
                max_start_attempts=max_start_attempts,
                start_timeout=start_timeout,
            )
            yield self
        finally:
            self.terminate()

    @contextlib.contextmanager
    def stopped(
        self,
        before_stop_callback: Optional[Callable[['Daemon'], None]] = None,
        after_stop_callback: Optional[Callable[['Daemon'], None]] = None,
        before_start_callback: Optional[Callable[['Daemon'], None]] = None,
        after_start_callback: Optional[Callable[['Daemon'], None]] = None,
    ) -> Generator['Daemon', None, None]:
        """
        Stop the daemon and return it's instance so it can be used as a context manager.

        Keyword Arguments:
            before_stop_callback:
                A callable to run before stopping the daemon. The callback must accept one argument,
                the daemon instance.
            after_stop_callback:
                A callable to run after stopping the daemon. The callback must accept one argument,
                the daemon instance.
            before_start_callback:
                A callable to run before starting the daemon. The callback must accept one argument,
                the daemon instance.
            after_start_callback:
                A callable to run after starting the daemon. The callback must accept one argument,
                the daemon instance.

        This context manager will stop the factory while the context is in place, it re-starts it once out of
        context.

        Example:
            .. code-block:: python

                assert factory.is_running() is True

                with factory.stopped():
                    assert factory.is_running() is False

                assert factory.is_running() is True
        """
        if not self.is_running():
            raise FactoryNotRunning('{0} is not running '.format(self))
        start_arguments = self.impl.get_start_arguments()
        try:
            if before_stop_callback:
                try:
                    before_stop_callback(self)
                except CallbackException as exc:
                    log.info(
                        'Exception raised when running %s: %s',
                        format_callback_to_string(before_stop_callback),
                        exc,
                        exc_info=True,
                    )
            self.terminate()
            if after_stop_callback:
                try:
                    after_stop_callback(self)
                except CallbackException as exc:
                    log.info(
                        'Exception raised when running %s: %s',
                        format_callback_to_string(after_stop_callback),
                        exc,
                        exc_info=True,
                    )
            yield self
        except ShellUtilsException:
            raise
        else:
            if before_start_callback:
                try:
                    before_start_callback(self)
                except CallbackException as exc:
                    log.info(
                        'Exception raised when running %s: %s',
                        format_callback_to_string(before_start_callback),
                        exc,
                        exc_info=True,
                    )
            _started = self.start(*start_arguments.args, **start_arguments.kwargs)
            if _started:
                if after_start_callback:
                    try:
                        after_start_callback(self)
                    except CallbackException as exc:
                        log.info(
                            'Exception raised when running %s: %s',
                            format_callback_to_string(after_start_callback),
                            exc,
                            exc_info=True,
                        )

    def run_start_checks(self, started_at: float, timeout_at: float) -> bool:
        """
        Run checks to confirm that the daemon has started.
        """
        start_check_callbacks = list(self.get_start_check_callbacks())
        if not start_check_callbacks:
            log.debug('No start check callbacks to run for %s', self)
            return True
        checks_start_time = time.time()
        log.debug('%s is running start checks', self)
        while time.time() <= timeout_at:
            if not self.is_running():
                raise FactoryNotStarted('{0} is no longer running'.format(self))
            if not start_check_callbacks:
                break
            start_check = start_check_callbacks[0]
            try:
                ret = start_check(timeout_at)
                if ret is True:
                    start_check_callbacks.pop(0)
            except Exception as exc:
                log.info(
                    'Exception raised when running %s: %s',
                    start_check,
                    exc,
                    exc_info=True,
                )
        if start_check_callbacks:
            log.error(
                'Failed to run start check callbacks after %1.2f seconds for %s. Remaining start check callbacks: %s',
                time.time() - checks_start_time,
                self,
                start_check_callbacks,
            )
            return False
        log.debug('All start check callbacks executed for %s', self)
        return True

    def _check_listening_ports(self, timeout_at: float) -> bool:
        """
        Check if the defined ports are in a listening state.

        This callback will run when trying to assess if the daemon is ready
        to accept work by trying to connect to each of the ports it's supposed
        to be listening.
        """
        check_ports = set(self.get_check_ports())
        if not check_ports:
            log.debug('No ports to check connection to for %s', self)
            return True
        log.debug(
            'Listening ports to check for %s: %s', self, set(self.get_check_ports())
        )
        checks_start_time = time.time()
        while time.time() <= timeout_at:
            if not self.is_running():
                raise FactoryNotStarted('{0} is no longer running'.format(self))
            if not check_ports:
                break
            check_ports -= ports.get_connectable_ports(check_ports)
            if check_ports:
                time.sleep(1.5)
        else:
            log.error(
                'Failed to check ports after %1.2f seconds for %s. Remaining ports to check: %s',
                time.time() - checks_start_time,
                self,
                check_ports,
            )
            return False
        log.debug(
            'All listening ports checked for %s: %s', self, set(self.get_check_ports())
        )
        return True

    def _add_factory_to_stats_processes(self) -> None:
        if self.stats_processes is not None:
            display_name = self.get_display_name()
            self.stats_processes.add(display_name, self.pid)

    def _remove_factory_from_stats_processes(self) -> None:
        if self.stats_processes is not None:
            display_name = self.get_display_name()
            self.stats_processes.remove(display_name)

    def _terminate_processes_matching_listen_ports(self) -> None:
        if not self.listen_ports:
            return
        found_processes = []
        for process in psutil.process_iter(['connections']):
            try:
                for connection in process.connections():
                    if connection.status != psutil.CONN_LISTEN:
                        continue
                    if connection.laddr.port in self.check_ports:
                        found_processes.append(process)
                        break
            except psutil.AccessDenied:
                continue
            except psutil.ZombieProcess:
                continue
        if found_processes:
            log.debug(
                'The following processes were found listening on ports %s: %s',
                ', '.join([str(port) for port in self.listen_ports]),
                found_processes,
            )
            terminate_process_list(found_processes, kill=True, slow_stop=False)
        else:
            log.debug(
                'No astray processes were found listening on ports: %s',
                ', '.join([str(port) for port in self.listen_ports]),
            )

    def __enter__(self) -> 'Daemon':
        """
        Use class as a context manager.
        """
        if not self.is_running():
            raise RuntimeError(
                """Factory not yet started. Perhaps you're after something like:

with {}.started() as factory:
    yield factory""".format(
                    self.__class__.__name__
                )
            )
        return self

    def __exit__(self, *_: Any) -> None:
        """
        Exit the class context manager.
        """
        self.terminate()
