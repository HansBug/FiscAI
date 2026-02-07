import os.path

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
    def __init__(self, model: LLMModelTyping, default_max_retries: int = 5):
        super().__init__(
            model=model,
            history=LLMHistory().with_system_prompt(quick_render(
                template_file=os.path.join(os.path.dirname(__file__), 'params_extract.md')
            )),
            default_max_retries=default_max_retries,
        )


def extract_params_from_page(page: Page, model: LLMModelTyping = None, **params):
    task = ParamsExtractTask(model=model)
    return task.ask_then_parse(
        input_content=page.extract_text(),
        **params
    )


class TableBasedFixTask(CSVReturnLLMTask):
    def __init__(self, model: LLMModelTyping, default_max_retries: int = 5, return_dataframe: bool = True):
        super().__init__(
            model=model,
            history=LLMHistory().with_system_prompt(quick_render(
                template_file=os.path.join(os.path.dirname(__file__), 'table_fix.md')
            )),
            default_max_retries=default_max_retries,
            return_dataframe=return_dataframe,
        )


class TextBasedFixTask(CSVReturnLLMTask):
    def __init__(self, model: LLMModelTyping, default_max_retries: int = 5, return_dataframe: bool = True):
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
                            **params):
    if method == 'table':
        task = TableBasedFixTask(
            model=model,
            return_dataframe=return_dataframe,
        )
        return task.ask_then_parse(
            str(page.extract_table()),
            **params
        )
    elif method == 'text':
        task = TextBasedFixTask(
            model=model,
            return_dataframe=return_dataframe,
        )
        return task.ask_then_parse(
            page.extract_text(),
            **params
        )
    else:
        raise ValueError(f'Unknown extract method - {method!r}.')
