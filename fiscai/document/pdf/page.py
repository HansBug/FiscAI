"""
PDF page processing utilities for FiscAI document analysis.

This module provides specialized LLM-based tasks for extracting structured
information from PDF pages. It includes functionality for parameter extraction
and table data extraction using different methods (text-based or table-based).

The module contains the following main components:

* :class:`ParamsExtractTask` - Extract structured parameters from PDF page text
* :class:`TableBasedFixTask` - Extract and fix table data using table extraction
* :class:`TextBasedFixTask` - Extract and fix table data using text extraction
* :func:`extract_params_from_page` - Convenience function for parameter extraction
* :func:`extract_table_from_page` - Convenience function for table extraction

.. note::
   This module requires pdfplumber for PDF page handling and hbllmutils for
   LLM integration. Template files (params_extract.md, table_fix.md, text_fix.md)
   must be present in the same directory as this module.

.. warning::
   LLM-based extraction may require multiple retries for complex or poorly
   formatted PDF content. Configure appropriate retry limits based on your
   data quality requirements.

Example::

    >>> from pdfplumber import PDF
    >>> from fiscai.document.pdf.page import extract_params_from_page, extract_table_from_page
    >>> 
    >>> # Open PDF and extract parameters from first page
    >>> with PDF.open('document.pdf') as pdf:
    ...     page = pdf.pages[0]
    ...     params = extract_params_from_page(page, model='gpt-4')
    ...     print(params)
    {'invoice_number': 'INV-2024-001', 'date': '2024-01-15', 'total': 1250.00}
    >>> 
    >>> # Extract table data using table-based method
    >>> with PDF.open('report.pdf') as pdf:
    ...     page = pdf.pages[0]
    ...     df = extract_table_from_page(page, model='gpt-4', method='table')
    ...     print(df.head())
    >>> 
    >>> # Extract table data using text-based method
    >>> with PDF.open('report.pdf') as pdf:
    ...     page = pdf.pages[0]
    ...     csv_text = extract_table_from_page(
    ...         page, 
    ...         model='gpt-4', 
    ...         method='text',
    ...         return_dataframe=False
    ...     )
    ...     print(csv_text)

"""
import io
import json
import os.path
from pprint import pformat
from typing import Optional, List

import pandas as pd
from hbllmutils.history import LLMHistory
from hbllmutils.model import LLMModelTyping
from hbllmutils.template import quick_render
from pdfplumber.page import Page

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal

from ...task import JSONReturnLLMTask, CSVReturnLLMTask


class ParamsExtractTask(JSONReturnLLMTask):
    """
    LLM task for extracting structured parameters from PDF page text.

    This class extends :class:`JSONReturnLLMTask` to provide specialized
    functionality for extracting key-value parameters from PDF page content.
    It uses a template-based system prompt loaded from params_extract.md to
    guide the LLM in identifying and extracting relevant parameters.

    The task is designed to handle various document types where structured
    information needs to be extracted, such as invoices, forms, reports, or
    certificates. The LLM analyzes the text content and returns a JSON object
    containing the extracted parameters.

    :param model: The LLM model to use for parameter extraction.
    :type model: LLMModelTyping
    :param default_max_retries: Maximum number of retry attempts for parsing
                               failures. Defaults to 5.
    :type default_max_retries: int

    .. note::
       The params_extract.md template file must be present in the same directory
       as this module. This template defines the extraction instructions and
       expected output format for the LLM.

    .. warning::
       Extraction accuracy depends on the quality of the PDF text extraction
       and the LLM's ability to understand the document structure. Complex or
       poorly formatted documents may require multiple retries.

    Example::

        >>> from fiscai.document.pdf.page import ParamsExtractTask
        >>> from pdfplumber import PDF
        >>> 
        >>> # Initialize task with specific model
        >>> task = ParamsExtractTask(model='gpt-4', default_max_retries=10)
        >>> 
        >>> # Extract parameters from PDF page
        >>> with PDF.open('invoice.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     text = page.extract_text()
        ...     params = task.ask_then_parse(input_content=text)
        ...     print(params)
        {'invoice_number': 'INV-2024-001', 'date': '2024-01-15', 'amount': 1250.00}
        >>> 
        >>> # Use with custom retry limit
        >>> params = task.ask_then_parse(
        ...     input_content=text,
        ...     max_retries=3,
        ...     temperature=0.3
        ... )

    """

    def __init__(self, model: LLMModelTyping, default_max_retries: int = 5):
        """
        Initialize the ParamsExtractTask.

        :param model: The LLM model to use for parameter extraction.
        :type model: LLMModelTyping
        :param default_max_retries: Maximum number of retry attempts for parsing
                                   failures. Must be a positive integer. Defaults to 5.
        :type default_max_retries: int

        :raises FileNotFoundError: If the params_extract.md template file is not found.
        :raises ValueError: If default_max_retries is not a positive integer.

        Example::

            >>> from fiscai.document.pdf.page import ParamsExtractTask
            >>> 
            >>> # Simple initialization with defaults
            >>> task = ParamsExtractTask(model='gpt-4')
            >>> print(task.default_max_retries)
            5
            >>> 
            >>> # Initialize with custom retry limit
            >>> task = ParamsExtractTask(model='gpt-4', default_max_retries=10)
            >>> print(task.default_max_retries)
            10

        """
        super().__init__(
            model=model,
            history=LLMHistory().with_system_prompt(quick_render(
                template_file=os.path.join(os.path.dirname(__file__), 'params_extract.md')
            )),
            default_max_retries=default_max_retries,
        )


def extract_params_from_page(page: Page, model: LLMModelTyping = None,
                             ref_data: Optional[List[dict]] = None, **params):
    """
    Extract structured parameters from a PDF page using LLM analysis.

    This convenience function creates a :class:`ParamsExtractTask` instance and
    uses it to extract key-value parameters from the provided PDF page. The
    function extracts text from the page and passes it to the LLM for analysis.

    :param page: The PDF page object to extract parameters from.
    :type page: Page
    :param model: The LLM model to use for extraction. If None, uses the default
                 model configured in the environment.
    :type model: LLMModelTyping, optional
    :param params: Additional keyword arguments to pass to the LLM task's
                  ask_then_parse method (e.g., max_retries, temperature).
    :return: Dictionary containing the extracted parameters as key-value pairs.
    :rtype: dict

    :raises ValueError: If the page text cannot be extracted or is empty.
    :raises OutputParseFailed: If parameter extraction fails after all retry attempts.

    .. note::
       This function extracts all text from the page using pdfplumber's
       extract_text() method. For pages with complex layouts, consider
       preprocessing the text or using specific extraction regions.

    .. warning::
       The function creates a new task instance for each call. For processing
       multiple pages, consider creating a single :class:`ParamsExtractTask`
       instance and reusing it for better performance.

    Example::

        >>> from pdfplumber import PDF
        >>> from fiscai.document.pdf.page import extract_params_from_page
        >>> 
        >>> # Extract parameters from first page
        >>> with PDF.open('invoice.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     params = extract_params_from_page(page, model='gpt-4')
        ...     print(params)
        {'invoice_number': 'INV-2024-001', 'date': '2024-01-15', 'total': 1250.00}
        >>> 
        >>> # Extract with custom parameters
        >>> with PDF.open('form.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     params = extract_params_from_page(
        ...         page,
        ...         model='gpt-4',
        ...         max_retries=3,
        ...         temperature=0.2
        ...     )
        ...     print(params['applicant_name'])
        John Doe
        >>> 
        >>> # Process multiple pages
        >>> with PDF.open('document.pdf') as pdf:
        ...     all_params = []
        ...     for page in pdf.pages:
        ...         params = extract_params_from_page(page, model='gpt-4')
        ...         all_params.append(params)

    """
    task = ParamsExtractTask(model=model)
    with io.StringIO() as sf:
        if ref_data:
            print(f'# Reference Data', file=sf)
            print(f'', file=sf)
            print(f'```json', file=sf)
            print(pformat(ref_data), file=sf)
            print(f'```', file=sf)

        print(f'# Text To Extract Params From', file=sf)
        print(f'', file=sf)
        print(f'```text', file=sf)
        print(page.extract_text(), file=sf)
        print(f'```', file=sf)

        return task.ask_then_parse(
            input_content=sf.getvalue(),
            **params
        )


class TableBasedFixTask(CSVReturnLLMTask):
    """
    LLM task for extracting and fixing table data using table-based extraction.

    This class extends :class:`CSVReturnLLMTask` to provide specialized
    functionality for processing table data extracted directly from PDF pages
    using pdfplumber's table extraction capabilities. It uses a template-based
    system prompt loaded from table_fix.md to guide the LLM in cleaning and
    standardizing the extracted table data.

    The task is designed to handle tables that can be successfully extracted
    using pdfplumber's table detection, but may contain formatting issues,
    merged cells, or inconsistent data that needs LLM-based correction.

    :param model: The LLM model to use for table fixing.
    :type model: LLMModelTyping
    :param default_max_retries: Maximum number of retry attempts for parsing
                               failures. Defaults to 5.
    :type default_max_retries: int
    :param return_dataframe: If True, return a pandas DataFrame. If False,
                            return raw CSV text. Defaults to True.
    :type return_dataframe: bool

    .. note::
       The table_fix.md template file must be present in the same directory
       as this module. This template defines the fixing instructions and
       expected output format for the LLM.

    .. warning::
       This method works best when pdfplumber can successfully detect table
       structure. For tables with complex layouts or no clear borders,
       consider using :class:`TextBasedFixTask` instead.

    Example::

        >>> from fiscai.document.pdf.page import TableBasedFixTask
        >>> from pdfplumber import PDF
        >>> 
        >>> # Initialize task with DataFrame return
        >>> task = TableBasedFixTask(model='gpt-4', return_dataframe=True)
        >>> 
        >>> # Extract and fix table from PDF page
        >>> with PDF.open('report.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     table_data = page.extract_table()
        ...     df = task.ask_then_parse(input_content=str(table_data))
        ...     print(df)
              Product  Quantity  Price
        0      Laptop        10   999.99
        1       Mouse        50    25.00
        2    Keyboard        30    75.00
        >>> 
        >>> # Return raw CSV text
        >>> task_csv = TableBasedFixTask(model='gpt-4', return_dataframe=False)
        >>> csv_text = task_csv.ask_then_parse(input_content=str(table_data))
        >>> print(csv_text)
        Product,Quantity,Price
        Laptop,10,999.99
        Mouse,50,25.00
        Keyboard,30,75.00

    """

    def __init__(self, model: LLMModelTyping, default_max_retries: int = 5, return_dataframe: bool = True):
        """
        Initialize the TableBasedFixTask.

        :param model: The LLM model to use for table fixing.
        :type model: LLMModelTyping
        :param default_max_retries: Maximum number of retry attempts for parsing
                                   failures. Must be a positive integer. Defaults to 5.
        :type default_max_retries: int
        :param return_dataframe: If True, return a pandas DataFrame. If False,
                                return raw CSV text. Defaults to True.
        :type return_dataframe: bool

        :raises FileNotFoundError: If the table_fix.md template file is not found.
        :raises ValueError: If default_max_retries is not a positive integer.

        Example::

            >>> from fiscai.document.pdf.page import TableBasedFixTask
            >>> 
            >>> # Simple initialization with defaults
            >>> task = TableBasedFixTask(model='gpt-4')
            >>> print(task.return_dataframe)
            True
            >>> 
            >>> # Initialize with custom configuration
            >>> task = TableBasedFixTask(
            ...     model='gpt-4',
            ...     default_max_retries=10,
            ...     return_dataframe=False
            ... )
            >>> print(task.return_dataframe)
            False

        """
        super().__init__(
            model=model,
            history=LLMHistory().with_system_prompt(quick_render(
                template_file=os.path.join(os.path.dirname(__file__), 'table_fix.md')
            )),
            default_max_retries=default_max_retries,
            return_dataframe=return_dataframe,
        )


class TextBasedFixTask(CSVReturnLLMTask):
    """
    LLM task for extracting and fixing table data using text-based extraction.

    This class extends :class:`CSVReturnLLMTask` to provide specialized
    functionality for processing table data from plain text extracted from
    PDF pages. It uses a template-based system prompt loaded from text_fix.md
    to guide the LLM in identifying table structures within text and converting
    them to properly formatted CSV data.

    The task is designed to handle cases where table structure is not clearly
    defined or where pdfplumber's table extraction fails. The LLM analyzes
    the text content to identify tabular patterns and reconstructs the table
    in CSV format.

    :param model: The LLM model to use for table extraction and fixing.
    :type model: LLMModelTyping
    :param default_max_retries: Maximum number of retry attempts for parsing
                               failures. Defaults to 5.
    :type default_max_retries: int
    :param return_dataframe: If True, return a pandas DataFrame. If False,
                            return raw CSV text. Defaults to True.
    :type return_dataframe: bool

    .. note::
       The text_fix.md template file must be present in the same directory
       as this module. This template defines the extraction and fixing
       instructions for the LLM.

    .. warning::
       Text-based extraction is more prone to errors than table-based extraction,
       especially for complex table layouts. Consider increasing max_retries
       for better reliability.

    Example::

        >>> from fiscai.document.pdf.page import TextBasedFixTask
        >>> from pdfplumber import PDF
        >>> 
        >>> # Initialize task with DataFrame return
        >>> task = TextBasedFixTask(model='gpt-4', return_dataframe=True)
        >>> 
        >>> # Extract and fix table from PDF page text
        >>> with PDF.open('report.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     text = page.extract_text()
        ...     df = task.ask_then_parse(input_content=text)
        ...     print(df)
              Product  Quantity  Price
        0      Laptop        10   999.99
        1       Mouse        50    25.00
        2    Keyboard        30    75.00
        >>> 
        >>> # Return raw CSV text
        >>> task_csv = TextBasedFixTask(model='gpt-4', return_dataframe=False)
        >>> csv_text = task_csv.ask_then_parse(input_content=text)
        >>> print(csv_text)
        Product,Quantity,Price
        Laptop,10,999.99
        Mouse,50,25.00
        Keyboard,30,75.00

    """

    def __init__(self, model: LLMModelTyping, default_max_retries: int = 5, return_dataframe: bool = True):
        """
        Initialize the TextBasedFixTask.

        :param model: The LLM model to use for table extraction and fixing.
        :type model: LLMModelTyping
        :param default_max_retries: Maximum number of retry attempts for parsing
                                   failures. Must be a positive integer. Defaults to 5.
        :type default_max_retries: int
        :param return_dataframe: If True, return a pandas DataFrame. If False,
                                return raw CSV text. Defaults to True.
        :type return_dataframe: bool

        :raises FileNotFoundError: If the text_fix.md template file is not found.
        :raises ValueError: If default_max_retries is not a positive integer.

        Example::

            >>> from fiscai.document.pdf.page import TextBasedFixTask
            >>> 
            >>> # Simple initialization with defaults
            >>> task = TextBasedFixTask(model='gpt-4')
            >>> print(task.return_dataframe)
            True
            >>> 
            >>> # Initialize with custom configuration
            >>> task = TextBasedFixTask(
            ...     model='gpt-4',
            ...     default_max_retries=10,
            ...     return_dataframe=False
            ... )
            >>> print(task.return_dataframe)
            False

        """
        super().__init__(
            model=model,
            history=LLMHistory().with_system_prompt(quick_render(
                template_file=os.path.join(os.path.dirname(__file__), 'text_fix.md')
            )),
            default_max_retries=default_max_retries,
            return_dataframe=return_dataframe,
        )


def extract_table_from_page(page: Page, model: LLMModelTyping = None,
                            method: Literal['text', 'table'] = 'table', return_dataframe: bool = True,
                            ref_data: Optional[pd.DataFrame] = None, **params):
    """
    Extract table data from a PDF page using LLM-based processing.

    This convenience function provides a unified interface for extracting table
    data from PDF pages using either table-based or text-based extraction methods.
    It automatically creates the appropriate task instance based on the specified
    method and processes the page content.

    The function supports two extraction methods:
    
    - 'table': Uses pdfplumber's table extraction followed by LLM-based fixing
    - 'text': Uses text extraction followed by LLM-based table reconstruction

    :param page: The PDF page object to extract table data from.
    :type page: Page
    :param model: The LLM model to use for extraction. If None, uses the default
                 model configured in the environment.
    :type model: LLMModelTyping, optional
    :param method: Extraction method to use. Either 'table' for table-based
                  extraction or 'text' for text-based extraction. Defaults to 'table'.
    :type method: Literal['text', 'table']
    :param return_dataframe: If True, return a pandas DataFrame. If False,
                            return raw CSV text. Defaults to True.
    :type return_dataframe: bool
    :param params: Additional keyword arguments to pass to the task's
                  ask_then_parse method (e.g., max_retries, temperature).
    :return: Either a pandas DataFrame or CSV text string containing the
            extracted table data, depending on return_dataframe parameter.
    :rtype: pandas.DataFrame or str

    :raises ValueError: If an unknown extraction method is specified or if
                       table extraction fails for the table-based method.
    :raises OutputParseFailed: If table extraction fails after all retry attempts.

    .. note::
       The 'table' method generally provides better results for well-structured
       tables with clear borders. The 'text' method is more flexible but may
       be less accurate for complex layouts.

    .. warning::
       The function creates a new task instance for each call. For processing
       multiple pages, consider creating task instances once and reusing them
       for better performance.

    Example::

        >>> from pdfplumber import PDF
        >>> from fiscai.document.pdf.page import extract_table_from_page
        >>> 
        >>> # Extract table using table-based method (default)
        >>> with PDF.open('report.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     df = extract_table_from_page(page, model='gpt-4')
        ...     print(df)
              Product  Quantity  Price
        0      Laptop        10   999.99
        1       Mouse        50    25.00
        >>> 
        >>> # Extract table using text-based method
        >>> with PDF.open('report.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     df = extract_table_from_page(page, model='gpt-4', method='text')
        ...     print(df.shape)
        (3, 3)
        >>> 
        >>> # Get raw CSV text instead of DataFrame
        >>> with PDF.open('report.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     csv_text = extract_table_from_page(
        ...         page,
        ...         model='gpt-4',
        ...         method='table',
        ...         return_dataframe=False
        ...     )
        ...     print(csv_text)
        Product,Quantity,Price
        Laptop,10,999.99
        Mouse,50,25.00
        >>> 
        >>> # Extract with custom parameters
        >>> with PDF.open('complex.pdf') as pdf:
        ...     page = pdf.pages[0]
        ...     df = extract_table_from_page(
        ...         page,
        ...         model='gpt-4',
        ...         method='text',
        ...         max_retries=10,
        ...         temperature=0.3
        ...     )
        >>> 
        >>> # Process multiple pages with same method
        >>> with PDF.open('document.pdf') as pdf:
        ...     tables = []
        ...     for page in pdf.pages:
        ...         try:
        ...             df = extract_table_from_page(page, model='gpt-4', method='table')
        ...             tables.append(df)
        ...         except Exception as e:
        ...             print(f"Failed to extract table: {e}")

    """
    with io.StringIO() as sf:
        if ref_data:
            print(f'# Reference Data', file=sf)
            print(f'', file=sf)
            print(f'```', file=sf)
            print(ref_data, file=sf)
            print(f'```', file=sf)

        print(f'# Text To Extract Table From', file=sf)
        print(f'', file=sf)
        print(f'```json', file=sf)
        print(json.dumps(page.extract_table()), file=sf)
        print(f'```', file=sf)

        user_prompt = sf.getvalue()

    if method == 'table':
        task = TableBasedFixTask(
            model=model,
            return_dataframe=return_dataframe,
        )
        return task.ask_then_parse(
            input_content=user_prompt,
            **params
        )
    elif method == 'text':
        task = TextBasedFixTask(
            model=model,
            return_dataframe=return_dataframe,
        )
        return task.ask_then_parse(
            input_content=user_prompt,
            **params
        )
    else:
        raise ValueError(f'Unknown extract method - {method!r}.')
