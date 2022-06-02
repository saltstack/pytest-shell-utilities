# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
import functools
import logging
import pprint
import re
import sys
import time
from typing import List

import attr
import psutil
import pytest
from pytestskipmarkers.utils import platform

from pytestshellutils.exceptions import FactoryNotRunning
from pytestshellutils.exceptions import FactoryNotStarted
from pytestshellutils.shell import Daemon
from pytestshellutils.utils.processes import _get_cmdline
from tests.conftest import Tempfiles

try:
    from pytest import FixtureRequest
    from pytest import LogCaptureFixture
except ImportError:
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture

PROCESS_START_TIMEOUT = 2

log = logging.getLogger(__name__)


def kill_children(procs: List[psutil.Process]) -> None:  # pragma: no cover
    _, alive = psutil.wait_procs(procs, timeout=3)
    for p in alive:
        p.kill()


def test_daemon_process_termination(request: FixtureRequest, tempfiles: Tempfiles) -> None:
    primary_childrend_count = 5
    secondary_children_count = 3
    script = tempfiles.makepyfile(
        """
        #!{shebang}
        # coding=utf-8

        import time
        import multiprocessing

        def spin():
            while True:
                try:
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    break

        def spin_children():
            procs = []
            for idx in range({secondary_children_count}):
                proc = multiprocessing.Process(target=spin)
                proc.daemon = True
                proc.start()
                procs.append(proc)

            while True:
                try:
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    break


        def main():
            procs = []

            for idx in range({primary_childrend_count}):
                proc = multiprocessing.Process(target=spin_children)
                procs.append(proc)
                proc.start()

            while True:
                try:
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    break

            # We're not terminating child processes on purpose. Our code should handle it.

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """.format(
            shebang=sys.executable,
            primary_childrend_count=primary_childrend_count,
            secondary_children_count=secondary_children_count,
        ),
        executable=True,
    )
    if not platform.is_windows():
        daemon = Daemon(start_timeout=1, script_name=script)
    else:  # pragma: is-windows
        # Windows don't know how to handle python scripts directly
        daemon = Daemon(start_timeout=1, script_name=sys.executable, base_script_args=[script])
    daemon.start()
    daemon_pid = daemon.pid
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)
    # Allow the script to start
    time.sleep(PROCESS_START_TIMEOUT)
    assert psutil.pid_exists(daemon_pid)
    proc = psutil.Process(daemon_pid)
    children = proc.children(recursive=True)
    request.addfinalizer(functools.partial(kill_children, children))
    child_count = len(children)
    expected_count = primary_childrend_count + (primary_childrend_count * secondary_children_count)
    if platform.is_windows() and sys.version_info >= (3, 7):  # pragma: is-windows-ge-py37
        # After Python 3.7 there's an extra spawning process
        expected_count += 1
    if platform.is_darwin() and sys.version_info >= (3, 8):  # pragma: is-darwin-ge-py38
        # macOS defaults to spawning new processed after Python 3.8
        # Account for the forking process
        expected_count += 1
    assert child_count == expected_count, "{}!={}\n{}".format(
        child_count,
        expected_count,
        pprint.pformat([_get_cmdline(child) or child for child in children]),
    )
    daemon.terminate()
    assert psutil.pid_exists(daemon_pid) is False
    for child in list(children):  # pragma: no cover
        if psutil.pid_exists(child.pid):
            continue
        children.remove(child)
    assert not children, "len(children)=={} != 0\n{}".format(
        len(children), pprint.pformat([_get_cmdline(child) or child for child in children])
    )


@pytest.mark.skip("Will debug later")
def test_daemon_process_termination_parent_killed(
    request: FixtureRequest, tempfiles: Tempfiles
) -> None:

    primary_childrend_count = 5
    secondary_children_count = 3
    script = tempfiles.makepyfile(
        """
        #!{shebang}
        # coding=utf-8

        import time
        import multiprocessing

        def spin():
            while True:
                try:
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    break

        def spin_children():
            procs = []
            for idx in range({secondary_children_count}):
                proc = multiprocessing.Process(target=spin)
                proc.daemon = True
                proc.start()
                procs.append(proc)

            while True:
                try:
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    break

        def main():
            procs = []

            for idx in range({primary_childrend_count}):
                proc = multiprocessing.Process(target=spin_children)
                procs.append(proc)
                proc.start()

            while True:
                try:
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    break

            # We're not terminating child processes on purpose. Our code should handle it.

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """.format(
            shebang=sys.executable,
            primary_childrend_count=primary_childrend_count,
            secondary_children_count=secondary_children_count,
        ),
        executable=True,
    )
    if not platform.is_windows():
        daemon = Daemon(start_timeout=1, script_name=script)
    else:  # pragma: is-windows
        # Windows don't know how to handle python scripts directly
        daemon = Daemon(start_timeout=1, script_name=sys.executable, base_script_args=[script])
    daemon.start()
    daemon_pid = daemon.pid
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)
    # Allow the script to start
    time.sleep(PROCESS_START_TIMEOUT)
    assert psutil.pid_exists(daemon_pid)
    proc = psutil.Process(daemon_pid)
    children = proc.children(recursive=True)
    request.addfinalizer(functools.partial(kill_children, children))
    assert len(children) == primary_childrend_count + (
        primary_childrend_count * secondary_children_count
    )
    # Pretend the parent process died.
    proc.kill()
    time.sleep(0.5)
    # We should should still be able to terminate all child processes
    daemon.terminate()
    assert psutil.pid_exists(daemon_pid) is False
    psutil.wait_procs(children, timeout=3)
    for child in list(children):
        if psutil.pid_exists(child.pid):
            continue
        children.remove(child)
    assert not children, "len(children)=={} != 0\n{}".format(
        len(children), pprint.pformat(children)
    )


@pytest.mark.parametrize("start_timeout", [0.1, 0.3])
def test_started_context_manager(
    request: FixtureRequest, tempfiles: Tempfiles, start_timeout: float
) -> None:
    script = tempfiles.makepyfile(
        r"""
        # coding=utf-8

        import sys
        import time
        import multiprocessing

        def main():
            time.sleep(3)
            sys.stdout.write("Done!\n")
            sys.stdout.flush()
            sys.exit(0)

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """,
        executable=True,
    )
    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[script],
        start_timeout=2,
        max_start_attempts=1,
        check_ports=[12345],
    )
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)
    with pytest.raises(FactoryNotStarted) as exc:
        daemon.start(start_timeout=start_timeout)
    match = re.search(r"which took (?P<seconds>.*) seconds", str(exc.value))
    assert match
    # XXX: Revisit logic
    # seconds = float(match.group("seconds"))
    # Must take at least start_timeout to start
    # assert seconds > start_timeout
    # Should not take more than start_timeout + 0.3 to start and fail
    # assert seconds < start_timeout + 0.3

    # And using a context manager?
    with pytest.raises(FactoryNotStarted) as exc:
        started = None
        with daemon.started(start_timeout=start_timeout):
            # We should not even be able to set the following variable
            started = False  # pragma: no cover
    assert started is None
    match = re.search(r"which took (?P<seconds>.*) seconds", str(exc.value))
    assert match
    # XXX: Revisit logic
    # seconds = float(match.group("seconds"))
    # Must take at least start_timeout to start
    # assert seconds > start_timeout
    # Should not take more than start_timeout + 0.3 to start and fail
    # assert seconds < start_timeout + 0.3


@pytest.fixture
def factory_stopped_script(tempfiles: Tempfiles) -> str:
    return tempfiles.makepyfile(
        r"""
        # coding=utf-8

        import os
        import sys
        import time
        import socket
        import multiprocessing

        def main():

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', 12345))
            sock.listen(5)
            try:
                while True:
                    connection, address = sock.accept()
                    connection.close()
            except (KeyboardInterrupt, SystemExit):
                pass
            finally:
                sock.close()
            sys.exit(0)

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """,
        executable=True,
    )


def test_stopped_context_manager_raises_FactoryNotRunning(
    request: FixtureRequest, factory_stopped_script: str
) -> None:
    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[factory_stopped_script],
        start_timeout=3,
        max_start_attempts=1,
        check_ports=[12345],
    )
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)

    with pytest.raises(FactoryNotRunning):
        with daemon.stopped():
            pass  # pragma: no cover


def test_stopped_context_manager(request: FixtureRequest, factory_stopped_script: str) -> None:
    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[factory_stopped_script],
        start_timeout=3,
        max_start_attempts=1,
        check_ports=[12345],
    )
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)

    with daemon.started():
        assert daemon.is_running()
        with daemon.stopped():
            assert daemon.is_running() is False
        assert daemon.is_running()


@attr.s
class DaemonCallbackCounter:
    before_start_callback_counter = attr.ib(default=0)  # type: int
    after_start_callback_counter = attr.ib(default=0)  # type: int
    before_terminate_callback_counter = attr.ib(default=0)  # type: int
    after_terminate_callback_counter = attr.ib(default=0)  # type: int

    def before_start_callback(self) -> None:
        self.before_start_callback_counter += 1

    def after_start_callback(self) -> None:
        self.after_start_callback_counter += 1

    def before_terminate_callback(self) -> None:
        self.before_terminate_callback_counter += 1

    def after_terminate_callback(self) -> None:
        self.after_terminate_callback_counter += 1


@attr.s
class DaemonContextCallbackCounter:
    daemon = attr.ib()  # type: Daemon
    before_start_callback_counter = attr.ib(default=0)  # type: int
    after_start_callback_counter = attr.ib(default=0)  # type: int
    before_stop_callback_counter = attr.ib(default=0)  # type: int
    after_stop_callback_counter = attr.ib(default=0)  # type: int

    def before_start_callback(self, daemon: Daemon) -> None:
        assert daemon is self.daemon
        self.before_start_callback_counter += 1

    def after_start_callback(self, daemon: Daemon) -> None:
        assert daemon is self.daemon
        self.after_start_callback_counter += 1

    def before_stop_callback(self, daemon: Daemon) -> None:
        assert daemon is self.daemon
        self.before_stop_callback_counter += 1

    def after_stop_callback(self, daemon: Daemon) -> None:
        assert daemon is self.daemon
        self.after_stop_callback_counter += 1


def test_daemon_callbacks(request: FixtureRequest, factory_stopped_script: str) -> None:

    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[factory_stopped_script],
        start_timeout=3,
        max_start_attempts=1,
        check_ports=[12345],
    )
    callbacks = DaemonCallbackCounter()
    daemon.before_start(callbacks.before_start_callback)
    daemon.after_start(callbacks.after_start_callback)
    daemon.before_terminate(callbacks.before_terminate_callback)
    daemon.after_terminate(callbacks.after_terminate_callback)

    stopped_callbacks = DaemonContextCallbackCounter(daemon)

    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)

    daemon_started_once = False

    with daemon.started():
        daemon_started_once = daemon.is_running()
        assert daemon_started_once is True

        # Assert against the non context manager callbacks
        assert callbacks.before_start_callback_counter == 1
        assert callbacks.after_start_callback_counter == 1
        assert callbacks.before_terminate_callback_counter == 0
        assert callbacks.after_terminate_callback_counter == 0

        # Assert against the context manager callbacks
        assert stopped_callbacks.before_stop_callback_counter == 0
        assert stopped_callbacks.after_stop_callback_counter == 0
        assert stopped_callbacks.before_start_callback_counter == 0
        assert stopped_callbacks.after_start_callback_counter == 0

        with daemon.stopped(
            before_stop_callback=stopped_callbacks.before_stop_callback,
            after_stop_callback=stopped_callbacks.after_stop_callback,
            before_start_callback=stopped_callbacks.before_start_callback,
            after_start_callback=stopped_callbacks.after_start_callback,
        ):
            assert daemon.is_running() is False

            # Assert against the context manager callbacks
            assert stopped_callbacks.before_stop_callback_counter == 1
            assert stopped_callbacks.after_stop_callback_counter == 1
            assert stopped_callbacks.before_start_callback_counter == 0
            assert stopped_callbacks.after_start_callback_counter == 0

            # Assert against the non context manager callbacks
            assert callbacks.before_start_callback_counter == 1
            assert callbacks.after_start_callback_counter == 1
            assert callbacks.before_terminate_callback_counter == 1
            assert callbacks.after_terminate_callback_counter == 1

        assert daemon.is_running()

        # Assert against the context manager callbacks
        assert stopped_callbacks.before_stop_callback_counter == 1
        assert stopped_callbacks.after_stop_callback_counter == 1
        assert stopped_callbacks.before_start_callback_counter == 1
        assert stopped_callbacks.after_start_callback_counter == 1

        # Assert against the non context manager callbacks
        assert callbacks.before_start_callback_counter == 2
        assert callbacks.after_start_callback_counter == 2
        assert callbacks.before_terminate_callback_counter == 1
        assert callbacks.after_terminate_callback_counter == 1

        # Let's got through stopped again, the stopped_callbacks should not be called again
        # because they are not passed into .stopped()
        with daemon.stopped():
            assert daemon.is_running() is False
        assert daemon.is_running()

        # Assert against the context manager callbacks
        assert stopped_callbacks.before_stop_callback_counter == 1
        assert stopped_callbacks.after_stop_callback_counter == 1
        assert stopped_callbacks.before_start_callback_counter == 1
        assert stopped_callbacks.after_start_callback_counter == 1

    assert daemon_started_once is True

    # Assert against the non context manager callbacks
    assert callbacks.before_start_callback_counter == 3
    assert callbacks.after_start_callback_counter == 3
    assert callbacks.before_terminate_callback_counter == 3
    assert callbacks.after_terminate_callback_counter == 3


@attr.s
class DaemonStartCheckCounter:
    custom_start_check_1_callback_counter = attr.ib(default=0)  # type: int
    custom_start_check_2_callback_counter = attr.ib(default=0)  # type: int
    custom_start_check_3_callback_counter = attr.ib(default=0)  # type: int

    def custom_start_check_1_callback(self, timeout_at: float) -> bool:
        self.custom_start_check_1_callback_counter += 1
        if self.custom_start_check_1_callback_counter > 2:
            return True
        return False

    def custom_start_check_2_callback(self, timeout_at: float) -> bool:
        self.custom_start_check_2_callback_counter += 1
        if self.custom_start_check_2_callback_counter > 2:
            return True
        raise Exception("Foo!")

    def custom_start_check_3_callback(self, timeout_at: float) -> bool:
        self.custom_start_check_3_callback_counter += 1
        time.sleep(1)
        return False


def test_daemon_start_check_callbacks(request: FixtureRequest, factory_stopped_script: str) -> None:

    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[factory_stopped_script],
        start_timeout=3,
        max_start_attempts=1,
        check_ports=[12345],
    )
    callbacks = DaemonStartCheckCounter()
    daemon.start_check(callbacks.custom_start_check_1_callback)
    daemon.start_check(callbacks.custom_start_check_2_callback)

    daemon_start_check_callbacks = daemon.get_start_check_callbacks()

    with daemon.started():
        # Both start callbacks should have run 3 times by now, at which
        # time, they would have returned True
        pass

    assert callbacks.custom_start_check_1_callback_counter == 3
    assert callbacks.custom_start_check_2_callback_counter == 3

    # Assert that the list of callbacks is the same before running the start checks
    assert daemon.get_start_check_callbacks() == daemon_start_check_callbacks


def test_daemon_no_start_check_callbacks(request: FixtureRequest, tempfiles: Tempfiles) -> None:
    script = tempfiles.makepyfile(
        r"""
        # coding=utf-8

        import sys
        import time
        import multiprocessing

        def main():
            time.sleep(3)
            sys.stdout.write("Done!\n")
            sys.stdout.flush()
            sys.exit(0)

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """,
        executable=True,
    )
    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[script],
        start_timeout=2,
        max_start_attempts=1,
    )
    # Remove the check ports callback
    daemon._start_checks_callbacks.clear()
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)
    with daemon.started():
        # Daemon started without running any start checks
        pass
    assert not daemon.get_start_check_callbacks()


def test_daemon_start_check_callbacks_factory_not_running(
    request: FixtureRequest, tempfiles: Tempfiles
) -> None:
    script = tempfiles.makepyfile(
        r"""
        # coding=utf-8

        import sys
        import time
        import multiprocessing

        def main():
            time.sleep(2)
            sys.stdout.write("Done!\n")
            sys.stdout.flush()
            sys.exit(0)

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """,
        executable=True,
    )

    callbacks = DaemonStartCheckCounter()

    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[script],
        start_timeout=2,
        max_start_attempts=1,
    )
    # Make sure the daemon is terminated no matter what
    request.addfinalizer(daemon.terminate)

    daemon.start_check(callbacks.custom_start_check_3_callback)
    with pytest.raises(FactoryNotStarted):
        daemon.start()
    # Make sure the callback was called at least once
    assert callbacks.custom_start_check_3_callback_counter > 1


def test_context_manager_returns_class_instance(tempfiles: Tempfiles) -> None:
    script = tempfiles.makepyfile(
        r"""
        # coding=utf-8

        import sys
        import time
        import multiprocessing

        def main():
            while True:
                try:
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    break
            sys.stdout.write("Done!\n")
            sys.stdout.flush()
            sys.exit(0)

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """,
        executable=True,
    )
    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[script],
        start_timeout=1,
        max_start_attempts=1,
    )

    # Without starting the factory
    started = d = None
    with pytest.raises(RuntimeError):
        with daemon as d:
            # We should not even be able to set the following variable
            started = d.is_running()  # pragma: no cover
    assert d is None
    assert started is None

    # After starting the factory
    started = False
    daemon.start()
    with daemon as d:
        # We should not even be able to set the following variable
        started = d.is_running()
    assert d.is_running() is False
    assert started is True

    # By starting the factory and passing timeout directly
    started = False
    with daemon.started(start_timeout=1) as d:
        # We should not even be able to set the following variable
        started = d.is_running()
    assert d.is_running() is False
    assert started is True

    # By starting the factory without any keyword arguments
    started = False
    with daemon.started() as d:
        # We should not even be able to set the following variable
        started = d.is_running()
    assert d.is_running() is False
    assert started is True


@pytest.mark.parametrize("max_start_attempts", [1, 2, 3])
def test_exact_max_start_attempts(
    tempfiles: Tempfiles, caplog: LogCaptureFixture, max_start_attempts: int
) -> None:
    """
    This test asserts that we properly report max_start_attempts.
    """
    script = tempfiles.makepyfile(
        r"""
        # coding=utf-8

        import sys
        import time
        import multiprocessing

        def main():
            time.sleep(0.125)
            sys.exit(1)

        # Support for windows test runs
        if __name__ == '__main__':
            multiprocessing.freeze_support()
            main()
        """,
        executable=True,
    )
    daemon = Daemon(
        script_name=sys.executable,
        base_script_args=[script],
        start_timeout=0.1,
        max_start_attempts=max_start_attempts,
        check_ports=[12345],
    )
    with caplog.at_level(logging.INFO):
        with pytest.raises(FactoryNotStarted) as exc:
            daemon.start()
        assert "confirm running status after {} attempts".format(max_start_attempts) in str(
            exc.value
        )
    start_attempts = [
        "Attempt: {} of {}".format(n, max_start_attempts) for n in range(1, max_start_attempts + 1)
    ]
    for record in caplog.records:
        if not record.message.startswith("Starting Daemon"):
            continue
        for idx, start_attempt in enumerate(list(start_attempts)):
            if start_attempt in record.message:
                start_attempts.pop(idx)
    assert not start_attempts
