# find out all the txns and their import id
# find out txns to remove from their original files
# find out txns to update
# find out txns to append
# apply black with filter for remove & update
# append new txns
# apply black again
import collections
import json
import pathlib
import typing

from beancount_parser.parser import make_parser
from beancount_parser.parser import traverse
from lark import Lark
from lark import Tree

from .data_types import ChangeSet
from .data_types import GeneratedTransaction
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


def compute_changes(
    generated_txns: list[GeneratedTransaction], imported_txns: list[ImportedTransaction]
) -> dict[pathlib.Path, ChangeSet]:
    generated_id_txns = {txn.id: txn for txn in generated_txns}
    imported_id_txns = {txn.id: txn for txn in imported_txns}

    to_remove = collections.defaultdict(list)
    for txn in imported_txns:
        generated_txn = generated_id_txns.get(txn.id)
        if generated_txn is not None and txn.file != generated_txn.file:
            # it appears that the generated txn's file is different from the old one, let's remove it
            to_remove[txn.file].append(txn)

    to_add = collections.defaultdict(list)
    to_update = collections.defaultdict(list)
    for txn in generated_txns:
        imported_txn = imported_id_txns.get(txn.id)
        if imported_txn is None:
            to_add[pathlib.Path(txn.file)].append(txn)
        else:
            to_update[pathlib.Path(txn.file)].append(txn)

    all_files = frozenset(to_remove.keys()).union(to_add.keys()).union(to_update.keys())
    return {
        file_path: ChangeSet(
            remove=to_remove[file_path],
            add=to_add[file_path],
            update=to_update[file_path],
        )
        for file_path in all_files
    }
