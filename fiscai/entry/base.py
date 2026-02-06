"""
Base entry point utilities for FiscAI CLI applications.

This module provides foundational components for building Click-based command-line
interfaces with standardized error handling, exception management, and user feedback
mechanisms. It serves as the core infrastructure for all FiscAI CLI commands.

The module contains the following main components:

* :class:`ClickWarningException` - Warning-level exception with yellow output
* :class:`ClickErrorException` - Error-level exception with red output
* :class:`KeyboardInterrupted` - Graceful keyboard interruption handling
* :func:`print_exception` - Formatted exception output utility
* :func:`command_wrap` - Comprehensive error handling decorator for Click commands

.. note::
   This module is designed to work exclusively with Click-based CLI applications
   and requires the Click library to be installed.

.. warning::
   The command_wrap decorator should be applied after Click decorators to ensure
   proper exception handling within the Click context.

Example::

    >>> import click
    >>> from fiscai.entry.base import command_wrap, ClickErrorException
    >>> 
    >>> @click.command()
    >>> @click.option('--input', required=True, help='Input file path')
    >>> @command_wrap()
    >>> def process_file(input):
    ...     '''Process the input file with error handling.'''
    ...     if not os.path.exists(input):
    ...         raise ClickErrorException(f"File not found: {input}")
    ...     click.echo(f"Processing {input}...")
    >>> 
    >>> # The command now has comprehensive error handling including
    >>> # keyboard interrupts, unexpected errors, and custom exceptions

"""

import builtins
import itertools
import os
import sys
import traceback
from functools import wraps, partial
from typing import Optional, IO, Callable

import click
from click.exceptions import ClickException

CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help']
)


class ClickWarningException(ClickException):
    """
    Custom exception class for displaying warning messages in yellow color.

    This exception class extends Click's base ClickException to provide
    warning-level feedback to users with yellow-colored output, making it
    visually distinct from errors while still being handled by Click's
    exception system.

    :param message: The warning message to display to the user
    :type message: str

    .. note::
       The warning message is always displayed to stderr with yellow color,
       regardless of the terminal's color support settings.

    Example::

        >>> from fiscai.entry.base import ClickWarningException
        >>> raise ClickWarningException("This is a warning message")
        # Output in yellow: Error: This is a warning message

    """

    def show(self, file: Optional[IO] = None) -> None:
        """
        Display the warning message in yellow color to stderr.

        This method overrides the base ClickException.show() to provide
        custom colored output for warning messages. The message is always
        written to stderr to maintain consistency with standard error
        reporting conventions.

        :param file: File stream to write the output to (currently unused,
                    always writes to stderr)
        :type file: Optional[IO]

        .. note::
           The file parameter is kept for API compatibility but is not used.
           Output always goes to sys.stderr.

        """
        click.secho(self.format_message(), fg='yellow', file=sys.stderr)


class ClickErrorException(ClickException):
    """
    Custom exception class for displaying error messages in red color.

    This exception class extends Click's base ClickException to provide
    error-level feedback to users with red-colored output, making critical
    issues immediately visible in the terminal output.

    :param message: The error message to display to the user
    :type message: str

    .. note::
       The error message is always displayed to stderr with red color,
       providing clear visual distinction from warnings and normal output.

    Example::

        >>> from fiscai.entry.base import ClickErrorException
        >>> raise ClickErrorException("Critical error occurred")
        # Output in red: Error: Critical error occurred

    """

    def show(self, file: Optional[IO] = None) -> None:
        """
        Display the error message in red color to stderr.

        This method overrides the base ClickException.show() to provide
        custom colored output for error messages. The message is always
        written to stderr following standard error reporting conventions.

        :param file: File stream to write the output to (currently unused,
                    always writes to stderr)
        :type file: Optional[IO]

        .. note::
           The file parameter is kept for API compatibility but is not used.
           Output always goes to sys.stderr.

        """
        click.secho(self.format_message(), fg='red', file=sys.stderr)


def print_exception(err: BaseException, print: Optional[Callable] = None) -> None:
    """
    Print formatted exception information including full traceback.

    This utility function provides detailed exception reporting by printing
    the complete traceback and exception details in a readable format. It
    supports custom print functions for flexible output handling.

    :param err: The exception object to print information about
    :type err: BaseException
    :param print: Custom print function for output. If None, uses built-in print
    :type print: Optional[Callable]

    .. note::
       The traceback is formatted with line breaks preserved for readability,
       and exception arguments are displayed according to their count.

    Example::

        >>> from fiscai.entry.base import print_exception
        >>> try:
        ...     1 / 0
        ... except ZeroDivisionError as e:
        ...     print_exception(e)
        Traceback (most recent call last):
          File "<stdin>", line 2, in <module>
        ZeroDivisionError: division by zero
        >>> 
        >>> # With custom print function
        >>> import functools
        >>> import click
        >>> try:
        ...     raise ValueError("Custom error", 123)
        ... except ValueError as e:
        ...     print_exception(e, functools.partial(click.secho, fg='red'))
        # Output in red with traceback

    """
    print = print or builtins.print

    lines = list(itertools.chain(*map(
        lambda x: x.splitlines(keepends=False),
        traceback.format_tb(err.__traceback__)
    )))

    if lines:
        print('Traceback (most recent call last):')
        print(os.linesep.join(lines))

    if len(err.args) == 0:
        print(f'{type(err).__name__}')
    elif len(err.args) == 1:
        print(f'{type(err).__name__}: {err.args[0]}')
    else:
        print(f'{type(err).__name__}: {err.args}')


class KeyboardInterrupted(ClickWarningException):
    """
    Exception class for handling keyboard interruption (Ctrl+C) events.

    This exception provides a user-friendly way to handle KeyboardInterrupt
    exceptions in Click-based CLI applications, converting them into
    warning-level exceptions with appropriate exit codes and messages.

    :param msg: Custom interruption message. If None, defaults to 'Interrupted.'
    :type msg: Optional[str]

    :ivar exit_code: Exit code returned when this exception is raised (0x7 = 7)
    :vartype exit_code: int

    .. note::
       The exit code 0x7 (7) is used to distinguish keyboard interruptions
       from other types of errors in the application.

    Example::

        >>> from fiscai.entry.base import KeyboardInterrupted
        >>> raise KeyboardInterrupted()
        # Output in yellow: Error: Interrupted.
        # Exit code: 7
        >>> 
        >>> raise KeyboardInterrupted("User cancelled operation")
        # Output in yellow: Error: User cancelled operation
        # Exit code: 7

    """
    exit_code = 0x7

    def __init__(self, msg: Optional[str] = None):
        """
        Initialize the keyboard interruption exception.

        :param msg: Custom message to display. Defaults to 'Interrupted.' if None
        :type msg: Optional[str]

        """
        ClickWarningException.__init__(self, msg or 'Interrupted.')


def command_wrap():
    """
    Decorator factory for wrapping Click commands with comprehensive error handling.

    This decorator provides a standardized error handling mechanism for Click
    commands, catching and appropriately handling various exception types
    including Click exceptions, keyboard interrupts, and unexpected errors.

    The decorator performs the following error handling:

    * Passes through ClickException instances unchanged
    * Converts KeyboardInterrupt to KeyboardInterrupted exception
    * Catches unexpected exceptions, displays detailed error information,
      and exits with code 1

    :return: Decorator function that wraps Click command functions
    :rtype: Callable

    .. warning::
       This decorator should be applied after Click decorators to ensure
       proper exception handling within the Click context.

    Example::

        >>> import click
        >>> from fiscai.entry.base import command_wrap
        >>> 
        >>> @click.command()
        >>> @click.option('--value', type=int, required=True)
        >>> @command_wrap()
        >>> def process_value(value):
        ...     '''Calculate 100 divided by the input value.'''
        ...     result = 100 / value
        ...     click.echo(f"Result: {result}")
        >>> 
        >>> # Handles keyboard interruption gracefully
        >>> # Handles unexpected errors with detailed traceback
        >>> # Passes through Click exceptions normally

    """

    def _decorator(func: Callable) -> Callable:
        """
        Decorator that wraps a function with error handling logic.

        :param func: The Click command function to wrap
        :type func: Callable
        :return: Wrapped function with error handling
        :rtype: Callable

        """
        @wraps(func)
        def _new_func(*args, **kwargs):
            """
            Wrapped function that executes the original function with error handling.

            :param args: Positional arguments passed to the original function
            :param kwargs: Keyword arguments passed to the original function
            :return: Return value from the original function
            :raises ClickException: Re-raised if caught from the original function
            :raises KeyboardInterrupted: Raised when KeyboardInterrupt is caught
            :raises SystemExit: Raised with exit code 1 for unexpected exceptions

            """
            try:
                return func(*args, **kwargs)
            except ClickException:
                raise
            except KeyboardInterrupt:
                raise KeyboardInterrupted
            except BaseException as err:
                click.secho('Unexpected error found when running pyfcstm!', fg='red', file=sys.stderr)
                print_exception(err, partial(click.secho, fg='red', file=sys.stderr))
                click.get_current_context().exit(1)

        return _new_func

    return _decorator
