"""
JSON response parsing utilities for LLM tasks.

This module provides specialized LLM task classes for handling JSON-formatted
responses from language models. It extends the base parsable task framework
to automatically parse and validate JSON outputs, with built-in error recovery
through the json_repair library.

The module contains the following main components:

* :class:`JSONReturnLLMTask` - LLM task that parses JSON responses with automatic repair

.. note::
   This module requires the json_repair library for robust JSON parsing that can
   handle malformed JSON outputs from language models.

.. warning::
   JSON parsing may fail if the model output is severely malformed or contains
   no valid JSON structure. Configure appropriate retry limits to handle such cases.

Example::

    >>> from fiscai.task.json import JSONReturnLLMTask
    >>> from hbllmutils.model import LLMModel
    >>> 
    >>> # Initialize task with model
    >>> model = LLMModel(...)
    >>> task = JSONReturnLLMTask(model, default_max_retries=3)
    >>> 
    >>> # Ask for JSON response
    >>> result = task.ask_then_parse(
    ...     input_content="List the top 3 programming languages in JSON format"
    ... )
    >>> print(result)
    {'languages': ['Python', 'JavaScript', 'Java']}
    >>> 
    >>> # Handle parsing with custom retries
    >>> result = task.ask_then_parse(
    ...     input_content="Return user data as JSON",
    ...     max_retries=5,
    ...     temperature=0.7
    ... )

"""

from typing import Optional

import json_repair
from hbllmutils.history import LLMHistory
from hbllmutils.model import LLMModelTyping
from hbllmutils.response import ParsableLLMTask, extract_code


class JSONReturnLLMTask(ParsableLLMTask):
    """
    LLM task specialized for parsing JSON-formatted responses.

    This class extends :class:`ParsableLLMTask` to handle JSON responses from
    language models. It automatically extracts code blocks from the response,
    repairs malformed JSON using the json_repair library, and returns the
    parsed JSON object.

    The task is particularly useful when working with LLMs that are instructed
    to return structured data in JSON format, as it handles common formatting
    issues and extraction of JSON from Markdown code blocks automatically.

    Features:
        - Automatic extraction of JSON from Markdown code blocks
        - Robust JSON parsing with automatic repair of malformed JSON
        - Configurable retry mechanism for parse failures
        - Preservation of conversation history across requests

    :param model: The LLM model to use for generating responses.
    :type model: LLMModel
    :param history: Optional conversation history. If None, a new empty history
                   will be created. The history tracks conversation context.
    :type history: Optional[LLMHistory]
    :param default_max_retries: Default maximum number of retry attempts for
                               parsing failures. Must be a positive integer.
                               Defaults to 5.
    :type default_max_retries: int

    :raises ValueError: If default_max_retries is not a positive integer.

    .. note::
       The json_repair library is used to handle common JSON formatting issues
       such as trailing commas, missing quotes, and unescaped characters that
       LLMs sometimes produce.

    .. warning::
       Extremely malformed responses that cannot be repaired will still cause
       parse failures. Ensure your prompts clearly specify the expected JSON
       format to minimize such issues.

    Example::

        >>> from fiscai.task.json import JSONReturnLLMTask
        >>> from hbllmutils.model import LLMModel
        >>> from hbllmutils.history import LLMHistory
        >>> 
        >>> # Simple initialization
        >>> model = LLMModel(...)
        >>> task = JSONReturnLLMTask(model)
        >>> 
        >>> # Initialize with custom retries
        >>> task = JSONReturnLLMTask(model, default_max_retries=10)
        >>> 
        >>> # Initialize with existing history
        >>> history = LLMHistory().with_system_prompt(
        ...     "You are a helpful assistant that returns data in JSON format."
        ... )
        >>> task = JSONReturnLLMTask(model, history=history)
        >>> 
        >>> # Ask for JSON response
        >>> result = task.ask_then_parse(
        ...     input_content="List 3 fruits with their colors in JSON"
        ... )
        >>> print(result)
        {'fruits': [
            {'name': 'apple', 'color': 'red'},
            {'name': 'banana', 'color': 'yellow'},
            {'name': 'grape', 'color': 'purple'}
        ]}
        >>> 
        >>> # Handle complex JSON structures
        >>> result = task.ask_then_parse(
        ...     input_content="Return user profile data as JSON",
        ...     max_retries=3,
        ...     temperature=0.5
        ... )
        >>> print(result['user']['name'])
        John Doe
        >>> 
        >>> # Automatic handling of code blocks
        >>> # Model returns: "{\"status\": \"success\"}"
        >>> result = task.ask_then_parse(input_content="Return status")
        >>> print(result)
        {'status': 'success'}

    """

    def __init__(self, model: LLMModelTyping, history: Optional[LLMHistory] = None, default_max_retries: int = 5):
        """
        Initialize the JSONReturnLLMTask.

        :param model: The LLM model to use for generating responses.
        :type model: LLMModel
        :param history: Optional conversation history. If None, a new empty history
                       will be created. The history tracks conversation context
                       across multiple interactions.
        :type history: Optional[LLMHistory]
        :param default_max_retries: Default maximum number of retry attempts for
                                   parsing failures. Must be a positive integer.
                                   This value is used when max_retries is not
                                   specified in ask_then_parse. Defaults to 5.
        :type default_max_retries: int

        :raises ValueError: If default_max_retries is not a positive integer.

        Example::

            >>> from fiscai.task.json import JSONReturnLLMTask
            >>> from hbllmutils.model import LLMModel
            >>> 
            >>> # Simple initialization with defaults
            >>> model = LLMModel(...)
            >>> task = JSONReturnLLMTask(model)
            >>> print(task.default_max_retries)
            5
            >>> 
            >>> # Initialize with custom default retries
            >>> task = JSONReturnLLMTask(model, default_max_retries=10)
            >>> print(task.default_max_retries)
            10
            >>> 
            >>> # Initialize with existing history
            >>> from hbllmutils.history import LLMHistory
            >>> history = LLMHistory().with_system_prompt(
            ...     "Always return responses in valid JSON format."
            ... )
            >>> task = JSONReturnLLMTask(model, history=history, default_max_retries=3)
            >>> len(task.history)
            1

        """
        super().__init__(model, history, default_max_retries)

    def _parse_and_validate(self, content: str):
        """
        Parse and validate JSON content from the model's response.

        This method extracts code blocks from the response content, attempts to
        repair any malformed JSON using json_repair, and returns the parsed JSON
        object. The method handles responses in two formats:

        1. Plain JSON text without code block markers
        2. JSON wrapped in Markdown code blocks (```json ... ```)

        The extraction is performed by :func:`extract_code`, which intelligently
        handles both formats. The json_repair library then processes the extracted
        text to handle common JSON formatting issues that LLMs may produce.

        :param content: The raw output string from the model containing JSON data.
                       May be plain JSON or JSON wrapped in Markdown code blocks.
        :type content: str

        :return: The parsed JSON object. Return type depends on the JSON structure
                (dict, list, str, int, float, bool, or None).
        :rtype: Union[dict, list, str, int, float, bool, None]

        :raises json.JSONDecodeError: If the content cannot be parsed as valid JSON
                                     even after repair attempts. This exception is
                                     caught by the retry mechanism.
        :raises ValueError: If no code blocks are found in the response or if
                           multiple ambiguous code blocks are present. This exception
                           is caught by the retry mechanism.

        .. note::
           The json_repair library can fix many common JSON issues including:
           - Trailing commas in arrays and objects
           - Missing quotes around keys
           - Single quotes instead of double quotes
           - Unescaped special characters
           - Missing closing brackets or braces

        .. warning::
           Severely malformed JSON that cannot be repaired will raise an exception
           and trigger a retry. Ensure prompts clearly specify JSON format requirements.

        Example::

            >>> task = JSONReturnLLMTask(model)
            >>> 
            >>> # Parse plain JSON
            >>> result = task._parse_and_validate('{"name": "John", "age": 30}')
            >>> print(result)
            {'name': 'John', 'age': 30}
            >>> 
            >>> # Parse JSON from code block
            >>> markdown_json = '''```json
            ... {
            ...     "status": "success",
            ...     "data": [1, 2, 3]
            ... }
            ... ```'''
            >>> result = task._parse_and_validate(markdown_json)
            >>> print(result)
            {'status': 'success', 'data': [1, 2, 3]}
            >>> 
            >>> # Parse and repair malformed JSON
            >>> malformed = "{'name': 'John', 'age': 30,}"  # Single quotes, trailing comma
            >>> result = task._parse_and_validate(malformed)
            >>> print(result)
            {'name': 'John', 'age': 30}
            >>> 
            >>> # Handle arrays
            >>> array_json = '[1, 2, 3, 4, 5]'
            >>> result = task._parse_and_validate(array_json)
            >>> print(result)
            [1, 2, 3, 4, 5]
            >>> 
            >>> # Handle nested structures
            >>> nested = '''```json
            ... {
            ...     "user": {
            ...         "name": "Alice",
            ...         "contacts": ["email", "phone"]
            ...     }
            ... }
            ... ```'''
            >>> result = task._parse_and_validate(nested)
            >>> print(result['user']['name'])
            Alice

        """
        return json_repair.loads(extract_code(content))
