import json
import os.path

import pdfplumber
from hbllmutils.model import LLMModelTyping
from tqdm import tqdm

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal

from .init import get_document_file_in_doc_directory, DocumentMetadata
from ..pdf import extract_table_from_page
from ...document.pdf import extract_params_from_page
from ...utils import file_recovery_on_error


def extract_pdf_pages(doc_dir: str, method: Literal['text', 'table'] = 'table', model: LLMModelTyping = None):
    metadata = DocumentMetadata.load_from_directory(doc_dir)
    document_file = get_document_file_in_doc_directory(doc_dir, metadata)

    with pdfplumber.open(document_file) as pdf:
        ref_params, ref_table = None, None
        for page_num, page in enumerate(tqdm(pdf.pages, desc=f'Scanning Existed Pages'), start=1):
            dst_params_file = os.path.join(doc_dir, f'page-{page_num}-params.json')
            dst_table_file = os.path.join(doc_dir, f'page-{page_num}-table.csv')

            if ref_params is None and os.path.exists(dst_params_file):
                with open(dst_params_file, 'r') as f:
                    ref_params = json.load(f)
            if ref_table is None and os.path.exists(dst_table_file):
                with open(dst_table_file, 'r') as f:
                    ref_table = f.read()
            if ref_params is not None and ref_table is not None:
                break

        for page_num, page in enumerate(tqdm(pdf.pages, desc=f'Extract Pages From {metadata.filename}'), start=1):
            dst_params_file = os.path.join(doc_dir, f'page-{page_num}-params.json')
            dst_table_file = os.path.join(doc_dir, f'page-{page_num}-table.csv')

            if not os.path.exists(dst_params_file):
                with file_recovery_on_error([dst_params_file]):
                    params_data = extract_params_from_page(
                        page=page,
                        model=model,
                        ref_data=ref_params,
                    )
                    if ref_params is None:
                        ref_params = params_data
                    with open(dst_params_file, 'w') as f:
                        json.dump(params_data, f, ensure_ascii=False, sort_keys=True, indent=4)

            if not os.path.exists(dst_table_file):
                with file_recovery_on_error([dst_table_file]):
                    table_data = extract_table_from_page(
                        page=page,
                        model=model,
                        ref_data=ref_table,
                        method=method,
                        return_dataframe=False
                    )
                    if ref_table is None:
                        ref_table = table_data
                    with open(dst_table_file, 'w') as f:
                        print(table_data, file=f)
