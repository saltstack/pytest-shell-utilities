.. _changelog:

=========
Changelog
=========

Versions follow `Semantic Versioning <https://semver.org>`_ (`<major>.<minor>.<patch>`).

Backward incompatible (breaking) changes will only be introduced in major versions with advance notice in the
**Deprecations** section of releases.

.. towncrier-draft-entries::

.. towncrier release notes start

shell-utilities 1.5.0 (2022-06-02)
==================================

Improvements
------------

- The minimum python for the code base is now 3.7(we still provide support to Py3.5 and Py3.6 by providing a downgraded source, transparent to the user), and the project is now 100% typed, including the test suite. (`#26 <https://github.com/saltstack/pytest-shell-utilities/issues/26>`_)


Improved Documentation
----------------------

- Improve and switch to google style docstrings (`#24 <https://github.com/saltstack/pytest-shell-utilities/issues/24>`_)


shell-utilities 1.4.0 (2022-05-26)
==================================

Improvements
------------

- ``Daemon.started()`` is now a context manager (`#22 <https://github.com/saltstack/pytest-shell-utilities/issues/22>`_)


shell-utilities 1.3.0 (2022-05-26)
==================================

Improvements
------------

- Support user provided callable functions to confirm that the daemon is up and running (`#20 <https://github.com/saltstack/pytest-shell-utilities/issues/20>`_)


shell-utilities 1.2.1 (2022-05-23)
==================================

Bug Fixes
---------

- Account for ``ProcessLookupError`` when terminating the underlying process. (`#18 <https://github.com/saltstack/pytest-shell-utilities/issues/18>`_)


shell-utilities 1.2.0 (2022-05-20)
==================================

Improvements
------------

- Revert `"Skip test when the GLIBC race conditions are met, instead of failing." <https://github.com/saltstack/pytest-shell-utilities/commit/f79aba3c5c0c7e4bdd895ae422d2f35ed22ea2e6>`_

  It wasn't the right fix/workaround. The right fix can be seen in `the Salt repo <https://github.com/saltstack/salt/pull/62078>`_ (`#16 <https://github.com/saltstack/pytest-shell-utilities/issues/16>`_)


Trivial/Internal Changes
------------------------

- Remove the redundant `wheel` dependency from pyproject.toml.

  The setuptools backend takes care of adding it automatically
  via `setuptools.build_meta.get_requires_for_build_wheel()` since day
  one.  The documentation has historically been wrong about listing it,
  and it has been fixed since.

  See https://github.com/pypa/setuptools/commit/f7d30a9529378cf69054b5176249e5457aaf640a (`#15 <https://github.com/saltstack/pytest-shell-utilities/issues/15>`_)


shell-utilities 1.1.0 (2022-05-16)
==================================

Improvements
------------

- Skip test when the GLIBC race conditions are met, instead of failing (`#13 <https://github.com/saltstack/pytest-shell-utilities/issues/13>`_)


Trivial/Internal Changes
------------------------

- Update pre-commit hooks and test against PyTest 7.0.x and 7.1.x. (`#13 <https://github.com/saltstack/pytest-shell-utilities/issues/13>`_)


shell-utilities 1.0.5 (2022-02-21)
==================================

Bug Fixes
---------

- Fix deprecation message telling to use the wrong property. (`#12 <https://github.com/saltstack/pytest-shell-utilities/issues/12>`_)


shell-utilities 1.0.4 (2022-02-17)
==================================

Improvements
------------

- State from which library the ``DeprecationWarning`` is coming from. (`#9 <https://github.com/saltstack/pytest-shell-utilities/issues/9>`_)


Bug Fixes
---------

- Handle ``None`` values for ``.stdout`` and ``.stderr`` on ``ProcessResult.__str__()`` (`#8 <https://github.com/saltstack/pytest-shell-utilities/issues/8>`_)


shell-utilities 1.0.3 (2022-02-16)
==================================

Bug Fixes
---------

- Fixed issue with ``sdist`` recompression for reproducible packages not iterating though subdirectories contents. (`#7 <https://github.com/saltstack/pytest-shell-utilities/issues/7>`_)


shell-utilities 1.0.2 (2022-02-05)
==================================

Bug Fixes
---------

- Set lower required python to `3.5.2` and avoid issues with `flake8-typing-imports`. (`#6 <https://github.com/saltstack/pytest-shell-utilities/issues/6>`_)


shell-utilities 1.0.1 (2022-01-25)
==================================

Bug Fixes
---------

- Stop casting ``None`` to a string for ``ProcessResult.std{out,err}`` (`#4 <https://github.com/saltstack/pytest-shell-utilities/issues/4>`_)


shell-utilities 1.0.0 (2022-01-25)
==================================

No significant changes.


shell-utilities 1.0.0rc7 (2022-01-25)
=====================================

Trivial/Internal Changes
------------------------

- Improvements before final RC

  * Add ``ProcessResult.std{out,err}.matcher`` example
  * Also generate reproducible packages when uploading a release to pypi
  * The ``twine-check`` nox target now call's the ``build`` target (`#3 <https://github.com/saltstack/pytest-shell-utilities/issues/3>`_)


shell-utilities 1.0.0rc6 (2022-01-24)
=====================================

No significant changes.


shell-utilities 1.0.0rc5 (2022-01-24)
=====================================

Trivial/Internal Changes
------------------------

- Provide a way to create reproducible distribution packages.

  * Stop customizing the ``towncrier`` template. (`#1 <https://github.com/saltstack/pytest-shell-utilities/issues/1>`_)


shell-utilities 1.0.0rc4 (2022-01-23)
=====================================

* ``ProcessResult.stdout`` and ``ProcessResult.stderr`` are now instances of
  ``pytestshellutils.utils.processes.MatchString`` which provides a ``.matcher``
  attribute that returns an instance of ``pytest.LineMatcher``.


shell-utilities 1.0.0rc3 (2022-01-21)
=====================================

* ``cwd`` and ``environ`` are now defined on ``BaseFactory``
* Add ``py.typed`` to state that the package is fully typed
* Fix the ``stacklevel`` value to point to the actual caller of the ``warn_until`` function.
* Fix the deprecated ``ProcessResult.json`` property.


shell-utilities 1.0.0rc2 (2022-01-21)
=====================================

* When passed a string, cast it to ``pathlib.Path`` before calling ``.resolve()``
* Extract ``BaseFactory`` from ``Factory``. It's required on `pytest-salt-factories`_ container
  implementation.


shell-utilities 1.0.0rc1 (2022-01-21)
=====================================

Pre-release of the first working version of the pytest plugin.


.. _pytest-salt-factories: https://github.com/saltstack/pytest-salt-factories
