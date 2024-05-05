# find out all the txns and their import id
# find out txns to remove from their original files
# find out txns to update
# find out txns to append
# apply black with filter for remove & update
# append new txns
# apply black again
import json
import pathlib
import typing

from beancount_parser.parser import make_parser
from beancount_parser.parser import traverse
from lark import Lark
from lark import Tree

from .data_types import ImportedTransaction


def extract_imported_transactions(
    parser: Lark, bean_file: pathlib.Path, import_id_key: str = "import-id"
) -> typing.Generator[ImportedTransaction, None, None]:
    last_txn = None
    for bean_path, tree in traverse(parser=parser, bean_file=bean_file):
        if tree.data != "start":
            raise ValueError("Expected start")
        for child in tree.children:
            if child is None:
                continue
            if child.data != "statement":
                raise ValueError("Expected statement")
            first_child = child.children[0]
            if not isinstance(first_child, Tree):
                continue
            if first_child.data == "date_directive":
                date_directive = first_child.children[0]
                directive_type = date_directive.data.value
                if directive_type != "txn":
                    continue
                last_txn = date_directive
            elif first_child.data == "metadata_item":
                metadata_key = first_child.children[0].value
                metadata_value = json.loads(first_child.children[1].value)
                if metadata_key == import_id_key:
                    yield ImportedTransaction(
                        file=bean_path, lineno=last_txn.meta.line, id=metadata_value
                    )
