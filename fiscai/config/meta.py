"""
Package metadata and version information module.

This module defines the core metadata constants for the fiscai package,
including version information, authorship details, and package description.
These constants are used throughout the package for identification and
are referenced by setup tools during package distribution.

The module contains the following metadata constants:

* :const:`__TITLE__` - Package name identifier
* :const:`__VERSION__` - Current package version following semantic versioning
* :const:`__DESCRIPTION__` - Brief package description for PyPI and documentation
* :const:`__AUTHOR__` - Package author name
* :const:`__AUTHOR_EMAIL__` - Contact email for package maintainer

.. note::
   This module follows semantic versioning (MAJOR.MINOR.PATCH) conventions.
   Version updates should reflect the nature of changes made to the package.

.. seealso::
   These constants are typically imported by setup.py and __init__.py files
   for package configuration and distribution purposes.

Example::

    >>> from fiscai.config.meta import __VERSION__, __TITLE__
    >>> print(f"{__TITLE__} version {__VERSION__}")
    fiscai version 0.0.1
    >>> 
    >>> # Access package metadata programmatically
    >>> from fiscai.config import meta
    >>> print(f"Author: {meta.__AUTHOR__} <{meta.__AUTHOR_EMAIL__}>")
    Author: HansBug <hansbug@buaa.edu.cn>

"""

#: str: Title of this project (should be `fiscai`).
#:
#: This constant defines the official package name used for PyPI distribution,
#: import statements, and package identification throughout the codebase.
__TITLE__ = "fiscai"

#: str: Version of this project.
#:
#: Version string following semantic versioning format (MAJOR.MINOR.PATCH).
#: - MAJOR: Incompatible API changes
#: - MINOR: Backwards-compatible functionality additions
#: - PATCH: Backwards-compatible bug fixes
#:
#: Current version indicates the package is in active development with
#: stable minor release features.
__VERSION__ = "0.0.1"

#: str: Short description of the project, will be included in ``setup.py``.
#:
#: This description appears on PyPI and in package metadata. It provides
#: a concise summary of the package's primary functionality and purpose,
#: highlighting its role as a utility library for Large Language Model
#: interactions with unified API support and conversation management.
__DESCRIPTION__ = ('A Python tool that uses LLMs to automatically categorize personal financial '
                   'transactions from bank/Alipay/WeChat PDF statements.')

#: str: Author of this project.
#:
#: Primary author and maintainer of the fiscai package.
__AUTHOR__ = "HansBug"

#: str: Email of the author.
#:
#: Contact email address for the package maintainer. This email can be used
#: for bug reports, feature requests, and general inquiries about the package.
__AUTHOR_EMAIL__ = "hansbug@buaa.edu.cn"
