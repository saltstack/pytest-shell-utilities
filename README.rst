.. image:: https://img.shields.io/github/workflow/status/saltstack/pytest-shell-utilities/Testing?style=plastic
   :target: https://github.com/saltstack/pytest-shell-utilities/actions/workflows/testing.yml
   :alt: CI


.. image:: https://readthedocs.org/projects/pytest-shell-utilities/badge/?style=plastic
   :target: https://pytest-shell-utilities.readthedocs.io
   :alt: Docs


.. image:: https://img.shields.io/codecov/c/github/saltstack/pytest-shell-utilities?style=plastic&token=ctdrjPj4mc
   :target: https://codecov.io/gh/saltstack/pytest-shell-utilities
   :alt: Codecov


.. image:: https://img.shields.io/pypi/pyversions/pytest-shell-utilities?style=plastic
   :target: https://pypi.org/project/pytest-shell-utilities
   :alt: Python Versions


.. image:: https://img.shields.io/pypi/wheel/pytest-shell-utilities?style=plastic
   :target: https://pypi.org/project/pytest-shell-utilities
   :alt: Python Wheel


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=plastic
   :target: https://github.com/psf/black
   :alt: Code Style: black


.. image:: https://img.shields.io/pypi/l/pytest-shell-utilities?style=plastic
   :alt: PyPI - License


..
   include-starts-here

==============================
What is Pytest Shell Utilities
==============================

   "When in doubt, shell out"

   -- Thomas S. Hatch


This pytest plugin was extracted from `pytest-salt-factories`_.
If provides a basic fixture ``shell`` which basically uses ``subprocess.Popen``
to run commands against the running system on a shell while providing a nice
assert'able return class.

.. _pytest-salt-factories: https://github.com/saltstack/pytest-salt-factories


Install
=======

Installing ``pytest-shell-utilities`` is as simple as:

.. code-block:: bash

   python -m pip install pytest-shell-utilities


And, that's honestly it.


Usage
=====

Once installed, you can now use the ``shell`` fixture to run some commands and assert against the
outcome.

.. code-block:: python

   def test_assert_good_exitcode(shell):

       ret = shell.run("exit", "0")
       assert ret.returncode == 0

   def test_assert_bad_exitcode(shell):

       ret = shell.run("exit", "1")
       assert ret.returncode == 1



If the command outputs parseable JSON, the ``shell`` fixture can attempt loading that output as
JSON which allows for asserting against the JSON loaded object.


.. code-block:: python

   def test_against_json_output(shell):
      d = {"a", "a", "b": "b"}
      ret = shell.run("echo", json.dumps(d))
      assert ret.data == d


..
   include-ends-here

Documentation
=============

The full documentation can be seen `here <https://pytest-shell-utilities.readthedocs.io>`_.
