# Copyright 2021-2023 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0
#
try:
    import coverage

    coverage.process_startup()
except ImportError:
    pass
