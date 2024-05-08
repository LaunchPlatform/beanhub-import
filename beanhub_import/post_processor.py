import collections
import copy
import itertools
import json
import pathlib
import typing

from beancount_parser.data_types import Entry
from beancount_parser.data_types import EntryType
from beancount_parser.helpers import collect_entries
from beancount_parser.parser import make_parser
from beancount_parser.parser import traverse
from lark import Lark
from lark import Tree

from . import constants
from .data_types import BeancountTransaction
from .data_types import ChangeSet
from .data_types import GeneratedPosting
from .data_types import GeneratedTransaction


def extract_existing_transactions(
    parser: Lark, bean_file: pathlib.Path, import_id_key: str = constants.IMPORT_ID_KEY
) -> typing.Generator[BeancountTransaction, None, None]:
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
                metadata_value = first_child.children[1]
                if (
                    metadata_key == import_id_key
                    and metadata_value.type == "ESCAPED_STRING"
                ):
                    yield BeancountTransaction(
                        file=bean_path,
                        lineno=last_txn.meta.line,
                        id=json.loads(metadata_value.value),
                    )


def compute_changes(
    generated_txns: list[GeneratedTransaction],
    imported_txns: list[BeancountTransaction],
    work_dir: pathlib.Path,
) -> dict[pathlib.Path, ChangeSet]:
    generated_id_txns = {txn.id: txn for txn in generated_txns}
    imported_id_txns = {txn.id: txn for txn in imported_txns}

    to_remove = collections.defaultdict(list)
    for txn in imported_txns:
        generated_txn = generated_id_txns.get(txn.id)
        if generated_txn is not None and txn.file.resolve() != (
            work_dir / generated_txn.file
        ):
            # it appears that the generated txn's file is different from the old one, let's remove it
            to_remove[txn.file].append(txn)

    to_add = collections.defaultdict(list)
    to_update = collections.defaultdict(dict)
    for txn in generated_txns:
        imported_txn = imported_id_txns.get(txn.id)
        generated_file = (work_dir / txn.file).resolve()
        if imported_txn is not None and imported_txn.file.resolve() == generated_file:
            to_update[generated_file][imported_txn.lineno] = txn
        else:
            to_add[generated_file].append(txn)

    all_files = frozenset(to_remove.keys()).union(to_add.keys()).union(to_update.keys())
    return {
        file_path: ChangeSet(
            remove=to_remove[file_path],
            add=to_add[file_path],
            update=to_update[file_path],
        )
        for file_path in all_files
    }


def to_parser_entry(parser: Lark, text: str) -> Entry:
    tree = parser.parse(text.strip())
    entries, _ = collect_entries(tree)
    if len(entries) != 1:
        raise ValueError("Expected exactly only one entry")
    return entries[0]


def posting_to_text(posting: GeneratedPosting) -> str:
    columns = [
        posting.account,
    ]
    if posting.amount is not None:
        columns.append(f"{posting.amount.number} {posting.amount.currency}")
    if posting.cost is not None:
        columns.append(posting.cost)
    if posting.price is not None:
        columns.append(f"@ {posting.price.number} {posting.price.currency}")
    return (" " * 2) + " ".join(columns)


def txn_to_text(
    txn: GeneratedTransaction,
) -> str:
    columns = [
        txn.date,
        txn.flag,
        *((json.dumps(txn.payee),) if txn.payee is not None else ()),
        json.dumps(txn.narration),
    ]
    line = " ".join(columns)
    import_src = None
    if txn.sources is not None:
        import_src = ":".join(txn.sources)
    return "\n".join(
        [
            line,
            f"  {constants.IMPORT_ID_KEY}: {json.dumps(txn.id)}",
            *(
                (f"  {constants.IMPORT_SRC_KEY}: {json.dumps(import_src)}",)
                if import_src is not None
                else ()
            ),
            *(map(posting_to_text, txn.postings)),
        ]
    )


def apply_change_set(
    tree: Lark,
    change_set: ChangeSet,
) -> Lark:
    if tree.data != "start":
        raise ValueError("expected start as the root rule")
    parser = make_parser()

    lines_to_remove = [txn.lineno for txn in change_set.remove]
    line_to_entries = {
        lineno: to_parser_entry(parser, txn_to_text(txn))
        for lineno, txn in change_set.update.items()
    }
    entries_to_add = [
        to_parser_entry(parser, txn_to_text(txn)) for txn in change_set.add
    ]

    new_tree = copy.deepcopy(tree)
    entries, tail_comments = collect_entries(new_tree)

    tailing_comments_entry: typing.Optional[Entry] = None
    if tail_comments:
        tailing_comments_entry = Entry(
            type=EntryType.COMMENTS,
            comments=tail_comments,
            statement=None,
            metadata=[],
            postings=[],
        )

    new_children = []
    for entry in itertools.chain(entries, entries_to_add):
        if entry.type == EntryType.COMMENTS:
            new_children.extend(entry.comments)
            continue
        if entry.statement.meta.line in lines_to_remove:
            # We also drop the comments
            continue
        actual_entry = line_to_entries.get(entry.statement.meta.line, entry)
        # use comments from existing entry regardless
        new_children.extend(entry.comments)
        new_children.append(actual_entry.statement)
        for metadata in actual_entry.metadata:
            new_children.extend(metadata.comments)
            new_children.append(metadata.statement)
        for posting in actual_entry.postings:
            new_children.extend(posting.comments)
            new_children.append(posting.statement)
            for metadata in posting.metadata:
                new_children.extend(metadata.comments)
                new_children.append(metadata.statement)

    if tailing_comments_entry is not None:
        new_children.extend(tailing_comments_entry.comments)

    new_tree.children = new_children
    return new_tree
