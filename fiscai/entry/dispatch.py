"""
Command-line interface dispatch module for fiscai.

This module provides the main CLI entry point and version information display
functionality for the fiscai package. It sets up the command-line interface
using Click framework and handles version display with author information.

The module contains the following main components:

* :func:`print_version` - Callback function to display version information
* :func:`fiscai` - Main CLI group entry point

.. note::
   This module uses Click framework for command-line interface construction.
   All CLI commands should be registered as subcommands to the main fiscai group.

Example::

    >>> # Command line usage
    >>> # fiscai --version
    >>> # fiscai, version 0.0.1.
    >>> # Developed by HansBug (hansbug@buaa.edu.cn).
    >>> 
    >>> # Display help information
    >>> # fiscai --help
    >>> # Usage: fiscai [OPTIONS] COMMAND [ARGS]...

"""

import click
from click.core import Context, Option

from .base import CONTEXT_SETTINGS
from ..config.meta import __TITLE__, __VERSION__, __AUTHOR__, __AUTHOR_EMAIL__, __DESCRIPTION__

# Parse author information from metadata
_raw_authors = [item.strip() for item in __AUTHOR__.split(',') if item.strip()]
_raw_emails = [item.strip() for item in __AUTHOR_EMAIL__.split(',')]

# Ensure email list matches author list length
if len(_raw_emails) < len(_raw_authors):  # pragma: no cover
    _raw_emails += [None] * (len(_raw_authors) - len(_raw_emails))
elif len(_raw_emails) > len(_raw_authors):  # pragma: no cover
    _raw_emails[len(_raw_authors) - 1] = tuple(_raw_emails[len(_raw_authors) - 1:])
    del _raw_emails[len(_raw_authors):]

# Create author-email tuples for formatting
_author_tuples = [
    (author, tuple([item for item in (email if isinstance(email, tuple) else ((email,) if email else ())) if item]))
    for author, email in zip(_raw_authors, _raw_emails)
]

# Format author strings with optional email addresses
_authors = [
    author if not emails else '{author} ({emails})'.format(author=author, emails=', '.join(emails))
    for author, emails in _author_tuples
]


# noinspection PyUnusedLocal
def print_version(ctx: Context, param: Option, value: bool) -> None:
    """
    Display version information and exit the CLI application.

    This callback function is triggered when the version flag is provided on the
    command line. It prints the application title, version number, and developer
    information, then exits the application gracefully.

    The function is designed to work as a Click callback and integrates with
    Click's option processing system. It respects Click's resilient parsing mode
    to avoid execution during shell completion or validation phases.

    :param ctx: Click context object containing execution state and configuration
    :type ctx: Context
    :param param: Metadata for the current parameter being processed (version option)
    :type param: Option
    :param value: Boolean value indicating whether the version flag was provided
    :type value: bool
    :return: None - function exits the application after printing version info
    :rtype: None

    .. note::
       This function is designed to be used as a Click callback and should not
       be called directly in normal code flow. It is automatically invoked when
       the ``--version`` or ``-v`` flag is provided.

    .. note::
       The function respects Click's resilient parsing mode and will not execute
       during completion or validation phases to avoid interfering with shell
       completion mechanisms.

    .. warning::
       This function calls ``ctx.exit()`` which terminates the application.
       No code after this function call will be executed in the normal flow.

    Example::

        >>> # This function is automatically called when using CLI
        >>> # $ fiscai --version
        >>> # fiscai, version 0.0.1.
        >>> # Developed by HansBug (hansbug@buaa.edu.cn).

    """
    if not value or ctx.resilient_parsing:
        return  # pragma: no cover
    
    # Display title and version information
    click.echo('{title}, version {version}.'.format(title=__TITLE__.capitalize(), version=__VERSION__))
    
    # Display author information if available
    if _authors:
        click.echo('Developed by {authors}.'.format(authors=', '.join(_authors)))
    
    # Exit the application
    ctx.exit()


@click.group(context_settings=CONTEXT_SETTINGS, help=__DESCRIPTION__)
@click.option('-v', '--version', is_flag=True,
              callback=print_version, expose_value=False, is_eager=True,
              help="Show fiscai's version information.")
def fiscai():
    """
    Main CLI group entry point for fiscai command-line interface.

    This function serves as the primary command group for the fiscai CLI
    application. It provides the foundation for all subcommands and handles
    global options such as version display and help information.

    The function is decorated with Click's group decorator to enable command
    grouping functionality, allowing subcommands to be registered and executed
    under the main fiscai command. It uses custom context settings defined in
    the base module and displays the application description from metadata.

    The version option is configured as an eager option, meaning it will be
    processed before other options and commands, allowing for immediate version
    display and exit.

    :return: None - serves as a command group container
    :rtype: None

    .. note::
       This function acts as a command group container and does not perform
       any operations directly. Actual functionality is provided by subcommands
       registered to this group using the ``@fiscai.command()`` decorator.

    .. note::
       Global options like ``--version`` and ``--help`` are available at this
       level and apply to the entire CLI application. The help option names
       are configured through CONTEXT_SETTINGS.

    .. note::
       The version option is marked as eager, which means it will be processed
       before any subcommands, allowing users to check the version without
       providing a valid subcommand.

    Example::

        >>> # Display help information
        >>> # $ fiscai --help
        >>> # Usage: fiscai [OPTIONS] COMMAND [ARGS]...
        >>> #
        >>> # A Python tool that uses LLMs to automatically categorize personal
        >>> # financial transactions from bank/Alipay/WeChat PDF statements.
        >>> #
        >>> # Options:
        >>> #   -v, --version  Show fiscai's version information.
        >>> #   -h, --help     Show this message and exit.
        >>> 
        >>> # Display version information
        >>> # $ fiscai --version
        >>> # fiscai, version 0.0.1.
        >>> # Developed by HansBug (hansbug@buaa.edu.cn).
        >>> 
        >>> # Execute a subcommand (when registered)
        >>> # $ fiscai process --input statement.pdf
        >>> # Processing financial statement...

    """
    pass  # pragma: no cover
