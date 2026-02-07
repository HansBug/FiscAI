"""
CSV data processing utilities for LLM-based tasks.

This module provides specialized LLM task classes for handling CSV data extraction
and processing. It enables language models to generate structured CSV output that
can be automatically parsed and validated, with optional conversion to pandas
DataFrames for further analysis.

The module contains the following main components:

* :class:`CSVReturnLLMTask` - LLM task for generating and parsing CSV responses

.. note::
   This module requires pandas for DataFrame conversion functionality.
   Ensure pandas is installed when using return_dataframe=True.

.. warning::
   CSV parsing may fail if the LLM generates malformed CSV output.
   The retry mechanism will attempt to regenerate valid CSV data.

Example::

    >>> from fiscai.task.csv import CSVReturnLLMTask
    >>> from hbllmutils.model import LLMModel
    >>> 
    >>> # Initialize model and task
    >>> model = LLMModel(...)
    >>> task = CSVReturnLLMTask(model, return_dataframe=True)
    >>> 
    >>> # Request CSV data generation
    >>> result = task.ask_then_parse(
    ...     input_content="Generate a CSV with columns: name, age, city"
    ... )
    >>> 
    >>> # Result is a pandas DataFrame
    >>> print(type(result))
    <class 'pandas.core.frame.DataFrame'>
    >>> print(result.head())
       name  age      city
    0  John   25  New York
    1  Jane   30    London

"""

import io
from typing import Optional

import pandas as pd
from hbllmutils.history import LLMHistory
from hbllmutils.model import LLMModelTyping
from hbllmutils.response import ParsableLLMTask, extract_code


class CSVReturnLLMTask(ParsableLLMTask):
    """
    LLM task specialized for generating and parsing CSV-formatted responses.

    This class extends :class:`ParsableLLMTask` to handle CSV data generation from
    language models. It automatically extracts code blocks containing CSV data,
    parses them using pandas, and optionally returns either a pandas DataFrame or
    the raw CSV text. The class includes built-in validation to ensure the generated
    CSV is well-formed and parseable.

    The parsing process:
    
    1. Extract CSV content from code blocks using :func:`extract_code`
    2. Parse CSV using pandas.read_csv with StringIO
    3. Validate that parsing succeeds without errors
    4. Return DataFrame or raw CSV text based on configuration

    :param model: The LLM model to use for generating CSV responses.
    :type model: LLMModel
    :param history: Optional conversation history. If None, a new empty history
                   will be created. The history maintains context across multiple
                   CSV generation requests.
    :type history: Optional[LLMHistory]
    :param default_max_retries: Default maximum number of retry attempts for parsing.
                               Must be a positive integer. Used when the LLM generates
                               malformed CSV that cannot be parsed. Defaults to 5.
    :type default_max_retries: int
    :param return_dataframe: If True, return a pandas DataFrame object. If False,
                            return the raw CSV text as a string. Defaults to True.
    :type return_dataframe: bool

    :ivar return_dataframe: Configuration flag controlling output format.
    :vartype return_dataframe: bool

    .. note::
       When return_dataframe=True, the returned DataFrame will have pandas default
       data types inferred from the CSV content. Consider explicit type conversion
       if specific dtypes are required.

    .. warning::
       Large CSV outputs may consume significant memory when converted to DataFrames.
       Consider using return_dataframe=False for very large datasets and process
       the CSV text incrementally.

    Example::

        >>> from fiscai.task.csv import CSVReturnLLMTask
        >>> from hbllmutils.model import LLMModel
        >>> from hbllmutils.history import LLMHistory
        >>> 
        >>> # Initialize with DataFrame return (default)
        >>> model = LLMModel(...)
        >>> task = CSVReturnLLMTask(model, return_dataframe=True)
        >>> 
        >>> # Generate CSV data
        >>> df = task.ask_then_parse(
        ...     input_content="Create a CSV with 3 products: name, price, stock"
        ... )
        >>> print(type(df))
        <class 'pandas.core.frame.DataFrame'>
        >>> print(df)
              name  price  stock
        0   Laptop    999     15
        1    Mouse     25     50
        2  Keyboard     75     30
        >>> 
        >>> # Initialize with raw CSV text return
        >>> task_raw = CSVReturnLLMTask(model, return_dataframe=False)
        >>> csv_text = task_raw.ask_then_parse(
        ...     input_content="Generate employee data CSV"
        ... )
        >>> print(type(csv_text))
        <class 'str'>
        >>> print(csv_text)
        name,department,salary
        Alice,Engineering,95000
        Bob,Marketing,75000
        >>> 
        >>> # Use with existing history and custom retries
        >>> history = LLMHistory().with_system_prompt(
        ...     "You are a data generator. Always output valid CSV format."
        ... )
        >>> task = CSVReturnLLMTask(
        ...     model,
        ...     history=history,
        ...     default_max_retries=10,
        ...     return_dataframe=True
        ... )
        >>> 
        >>> # Handle parsing errors with retry
        >>> try:
        ...     result = task.ask_then_parse(
        ...         input_content="Generate sales data CSV",
        ...         max_retries=3
        ...     )
        ... except OutputParseFailed as e:
        ...     print(f"Failed to generate valid CSV after {len(e.tries)} attempts")

    """

    def __init__(self, model: LLMModelTyping, history: Optional[LLMHistory] = None, default_max_retries: int = 5,
                 return_dataframe: bool = True):
        """
        Initialize the CSVReturnLLMTask.

        :param model: The LLM model to use for generating CSV responses.
        :type model: LLMModel
        :param history: Optional conversation history. If None, a new empty history
                       will be created. The history maintains context across multiple
                       CSV generation requests.
        :type history: Optional[LLMHistory]
        :param default_max_retries: Default maximum number of retry attempts for parsing.
                                   Must be a positive integer. Used when the LLM generates
                                   malformed CSV that cannot be parsed. Defaults to 5.
        :type default_max_retries: int
        :param return_dataframe: If True, return a pandas DataFrame object. If False,
                                return the raw CSV text as a string. Defaults to True.
        :type return_dataframe: bool

        :raises ValueError: If default_max_retries is not a positive integer.

        Example::

            >>> from fiscai.task.csv import CSVReturnLLMTask
            >>> from hbllmutils.model import LLMModel
            >>> 
            >>> # Simple initialization with defaults
            >>> model = LLMModel(...)
            >>> task = CSVReturnLLMTask(model)
            >>> print(task.return_dataframe)
            True
            >>> print(task.default_max_retries)
            5
            >>> 
            >>> # Initialize with custom configuration
            >>> task = CSVReturnLLMTask(
            ...     model,
            ...     default_max_retries=10,
            ...     return_dataframe=False
            ... )
            >>> print(task.return_dataframe)
            False
            >>> 
            >>> # Initialize with existing history
            >>> from hbllmutils.history import LLMHistory
            >>> history = LLMHistory().with_system_prompt(
            ...     "Generate CSV data with proper headers and formatting."
            ... )
            >>> task = CSVReturnLLMTask(model, history=history)
            >>> len(task.history)
            1

        """
        super().__init__(model, history, default_max_retries)
        self.return_dataframe = return_dataframe

    def _parse_and_validate(self, content: str):
        """
        Parse and validate CSV content from the model's response.

        This method extracts CSV data from code blocks in the model's response,
        parses it using pandas, and validates that it forms a well-structured
        DataFrame. The method handles both fenced code blocks and plain CSV text.

        The parsing process:
        
        1. Extract CSV content using :func:`extract_code` to handle code blocks
        2. Create a StringIO buffer from the extracted content
        3. Parse CSV using pandas.read_csv with default settings
        4. Return DataFrame or raw CSV text based on :attr:`return_dataframe`

        :param content: The raw response string from the model containing CSV data.
                       May be wrapped in code blocks (```csv or ```) or plain text.
        :type content: str

        :return: Either a pandas DataFrame (if return_dataframe=True) or the raw
                CSV text as a string (if return_dataframe=False).
        :rtype: pandas.DataFrame or str

        :raises ValueError: If the extracted content cannot be parsed as valid CSV.
                           Common causes include missing columns, inconsistent row
                           lengths, or malformed CSV syntax.
        :raises pandas.errors.ParserError: If pandas encounters CSV parsing errors
                                          such as quote mismatches or delimiter issues.
        :raises pandas.errors.EmptyDataError: If the extracted CSV content is empty.

        .. note::
           The method uses pandas default CSV parsing settings. For specialized
           CSV formats (custom delimiters, quote characters, etc.), consider
           overriding this method or post-processing the result.

        .. warning::
           This method does not perform semantic validation of CSV content.
           It only ensures the data is parseable as CSV. Additional validation
           of column names, data types, or value ranges should be implemented
           in subclasses if needed.

        Example::

            >>> task = CSVReturnLLMTask(model, return_dataframe=True)
            >>> 
            >>> # Parse fenced code block
            >>> content = '''```csv
            ... name,age,city
            ... Alice,30,NYC
            ... Bob,25,LA
            ... ```'''
            >>> result = task._parse_and_validate(content)
            >>> print(type(result))
            <class 'pandas.core.frame.DataFrame'>
            >>> print(result)
                name  age city
            0  Alice   30  NYC
            1    Bob   25   LA
            >>> 
            >>> # Parse plain CSV text
            >>> content = "product,price\\nLaptop,999\\nMouse,25"
            >>> result = task._parse_and_validate(content)
            >>> print(result)
              product  price
            0  Laptop    999
            1   Mouse     25
            >>> 
            >>> # Return raw CSV text
            >>> task_raw = CSVReturnLLMTask(model, return_dataframe=False)
            >>> result = task_raw._parse_and_validate(content)
            >>> print(type(result))
            <class 'str'>
            >>> print(result)
            product,price
            Laptop,999
            Mouse,25
            >>> 
            >>> # Handle parsing errors
            >>> invalid_content = '''```csv
            ... name,age
            ... Alice,30,extra_field
            ... ```'''
            >>> try:
            ...     result = task._parse_and_validate(invalid_content)
            ... except pandas.errors.ParserError as e:
            ...     print(f"CSV parsing failed: {e}")

        """
        content = extract_code(content)
        with io.StringIO(content) as sf:
            df = pd.read_csv(sf)

        if self.return_dataframe:
            return df
        else:
            return content
