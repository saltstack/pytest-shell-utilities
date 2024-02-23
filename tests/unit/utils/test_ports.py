# Copyright 2021-2024 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test the port related utilities.
"""
import functools
from typing import Any
from typing import List
from typing import Tuple
from unittest import mock

import pytest

import pytestshellutils.utils.ports as ports_utils


class MockedSocket:
    """
    This class is used so that we can return the known port in the getsockname call.
    """

    def __init__(self, port: int):
        self.port = port

    def bind(self, *args: Any, **kwargs: Any) -> None:
        pass

    def getsockname(self) -> Tuple[None, int]:
        return None, self.port

    def close(self) -> None:
        pass


class MockedCreateSocket:
    """
    This class just mocks the `socket.socket(...)` call so that we return the ports we want.
    """

    def __init__(self, ports: List[int]):
        self.ports = list(ports) + list(ports)

    def __call__(self, *args: Any, **kwargs: Any) -> MockedSocket:
        port = self.ports.pop(0)
        # Return a MockedSocket instance
        return MockedSocket(port)


def test_get_unused_localhost_port_cached() -> None:
    """
    Tests that test_get_unused_localhost_port only returns unique ports on consecutive calls.
    """
    num_calls = 10
    start_port = 1000
    # The ports we're gonna get back
    ports = []
    for port in range(start_port, start_port + num_calls):
        for _ in range(num_calls):
            # We make sure each port is repeated consecutively
            ports.append(port)

    # Hold a reference to the list of unique ports
    unique = set(ports)

    # This list will hold all ports that the function returns
    got_ports = []

    # We'll get the unique ports
    with mock.patch(
        "pytestshellutils.utils.socket.socket",
        new_callable=functools.partial(MockedCreateSocket, ports),
    ):
        for _ in range(num_calls):
            got_ports.append(ports_utils.get_unused_localhost_port(use_cache=True))
        assert len(got_ports) == num_calls
        assert set(got_ports) == unique

    with mock.patch(
        "pytestshellutils.utils.socket.socket",
        new_callable=functools.partial(MockedCreateSocket, ports + ports),
    ):
        for _ in range(num_calls):
            with pytest.raises(IndexError):
                # we won't have enough ports
                got_ports.append(ports_utils.get_unused_localhost_port(use_cache=True))
        # Since we couldn't get repeated ports, got_ports remains as it was
        assert len(got_ports) == num_calls
        assert set(got_ports) == unique

    # If we don't cache the port, we'll get repeated ports
    with mock.patch(
        "pytestshellutils.utils.socket.socket",
        new_callable=functools.partial(MockedCreateSocket, ports),
    ):
        for _ in range(num_calls):
            got_ports.append(ports_utils.get_unused_localhost_port())

        assert len(got_ports) == 2 * len(unique)
        assert set(got_ports) == unique
