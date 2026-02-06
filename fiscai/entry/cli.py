"""
Command-line interface entry point for fiscai package.

This module serves as the main CLI entry point for the fiscai package,
providing a unified command-line interface by composing various subcommands
through a decorator pattern. It aggregates functionality from different
modules to create a comprehensive CLI tool.

The module contains the following main components:

* :data:`cli` - Main CLI group that serves as the entry point for all commands

.. note::
   This module uses a decorator pattern to dynamically add subcommands to the
   main CLI group. New subcommands can be added by including their decorators
   in the _DECORATORS list.

Example::

    >>> # The CLI can be invoked from the command line:
    >>> # $ fiscai code pydoc --help
    >>> # $ fiscai code todo --help
    >>> 
    >>> # Or programmatically:
    >>> from fiscai.entry.cli import cli
    >>> cli()

"""

from .dispatch import fiscai

_DECORATORS = [
]

cli = fiscai
for deco in _DECORATORS:
    cli = deco(cli)
