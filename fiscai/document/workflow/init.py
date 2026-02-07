import json
import mimetypes
import os.path
import shutil
from typing import Literal, Optional

from pydantic import BaseModel, Field

from fiscai.utils import file_recovery_on_error

mimetypes.add_type('image/webp', '.webp')


class DocumentMetadata(BaseModel):
    """
    Metadata information for a document file.
    
    :param filename: The base filename of the document
    :type filename: str
    :param file_type: The general category of the file (pdf, word, excel, or image)
    :type file_type: Literal['pdf', 'word', 'excel', 'image']
    :param detailed_type: The specific format or version of the file type
    :type detailed_type: str
    """
    filename: str = Field(..., description="The base filename of the document")
    local_file: str = Field(..., description='Local file name in the document directory')
    file_type: Literal['pdf', 'word', 'excel', 'image'] = Field(
        ..., description="The general category of the file"
    )
    detailed_type: str = Field(..., description="The specific format or version of the file type")

    @classmethod
    def load_from_directory(cls, doc_dir):
        with open(get_metadata_file_in_doc_directory(doc_dir), 'r') as f:
            return cls.model_validate_json(f.read())


def get_document_metadata(doc_file: str) -> DocumentMetadata:
    filename = os.path.basename(doc_file)
    _, ext = os.path.splitext(os.path.normcase(doc_file))
    mimetype, _ = mimetypes.guess_type(doc_file)

    if mimetype and mimetype.startswith('application/pdf'):
        file_type = 'pdf'
        detailed_type = 'pdf'
    elif mimetype in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        file_type = 'word'
        if mimetype == 'application/msword':
            detailed_type = 'word2003'
        else:
            detailed_type = 'word2007+'
    elif mimetype in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        file_type = 'excel'
        if mimetype == 'application/vnd.ms-excel':
            detailed_type = 'excel2003'
        else:
            detailed_type = 'excel2007+'
    elif mimetype and mimetype.startswith('image/'):
        file_type = 'image'
        detailed_type = mimetype.split('/')[-1]
    else:
        raise ValueError(f"Unsupported file type: {mimetype or 'unknown'} for file {doc_file}")

    return DocumentMetadata(
        filename=filename,
        local_file=f'document{ext}',
        file_type=file_type,
        detailed_type=detailed_type,
    )


def init_for_doc(doc_file: str, dst_doc_dir: str):
    metadata = get_document_metadata(doc_file)
    dst_file = get_document_file_in_doc_directory(dst_doc_dir, metadata=metadata)
    dst_metadata_file = get_metadata_file_in_doc_directory(dst_doc_dir)

    with file_recovery_on_error([dst_file, dst_metadata_file]):
        os.makedirs(dst_doc_dir, exist_ok=True)
        with open(dst_metadata_file, 'w') as f:
            json.dump(metadata.model_dump(), f, sort_keys=True, ensure_ascii=False, indent=4)
        shutil.copyfile(doc_file, dst_file)


def get_metadata_file_in_doc_directory(doc_dir: str) -> str:
    return os.path.join(doc_dir, 'document_metadata.json')


def get_document_file_in_doc_directory(doc_dir: str, metadata: Optional[DocumentMetadata] = None) -> str:
    metadata = metadata or DocumentMetadata.load_from_directory(doc_dir)
    return os.path.join(doc_dir, metadata.local_file)
