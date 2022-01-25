.. _changelog:

=========
Changelog
=========

Versions follow `Semantic Versioning <https://semver.org>`_ (`<major>.<minor>.<patch>`).

Backward incompatible (breaking) changes will only be introduced in major versions with advance notice in the
**Deprecations** section of releases.

.. towncrier-draft-entries::

.. towncrier release notes start

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
