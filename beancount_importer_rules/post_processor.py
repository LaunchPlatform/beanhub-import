import collections
import copy
import json
import pathlib
import typing

from beancount_parser.data_types import Entry, EntryType
from beancount_parser.helpers import collect_entries
from beancount_parser.parser import make_parser, traverse
from lark import Lark, Tree

from beancount_importer_rules import constants
from beancount_importer_rules.data_types import (
    BeancountTransaction,
    ChangeSet,
    DeletedTransaction,
    GeneratedPosting,
    GeneratedTransaction,
)


def extract_existing_transactions(
    parser: Lark,
    bean_file: pathlib.Path,
    root_dir: pathlib.Path | None = None,
) -> typing.Generator[BeancountTransaction, None, None]:
    last_txn = None
    for bean_path, tree in traverse(
        parser=parser, bean_file=bean_file, root_dir=root_dir
    ):
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

            first_child_item = first_child.children[0]

            if (
                first_child.data == "date_directive"
                and not isinstance(first_child_item.data, str)
                and first_child_item.data.value == "txn"
            ):
                continue

            if first_child.data == "date_directive":
                last_txn = first_child_item
                continue

            if first_child.data == "metadata_item":
                metadata_key = first_child.children[0].value  # type: ignore
                metadata_value = first_child.children[1]
                if (
                    metadata_key == constants.IMPORT_ID_KEY
                    and metadata_value.type == "ESCAPED_STRING"  # type: ignore
                ):
                    yield BeancountTransaction(
                        file=bean_path,
                        lineno=last_txn.meta.line,  # type: ignore
                        id=json.loads(metadata_value.value),  # type: ignore
                    )


def compute_changes(
    generated_txns: list[GeneratedTransaction],
    imported_txns: list[BeancountTransaction],
    work_dir: pathlib.Path,
    deleted_txns: list[DeletedTransaction] | None = None,
) -> dict[pathlib.Path, ChangeSet]:
    generated_id_txns = {txn.id: txn for txn in generated_txns}
    imported_id_txns = {txn.id: txn for txn in imported_txns}
    deleted_txn_ids = set(txn.id for txn in (deleted_txns or ()))

    to_remove = collections.defaultdict(list)
    dangling_txns = collections.defaultdict(list)
    for txn in imported_txns:
        if txn.id in deleted_txn_ids:
            to_remove[txn.file].append(txn)
            continue
        generated_txn = generated_id_txns.get(txn.id)
        if (
            generated_txn is not None
            and txn.file.resolve() != (work_dir / generated_txn.file).resolve()
        ):
            # it appears that the generated txn's file is different from the old one, let's remove it
            to_remove[txn.file].append(txn)
        elif generated_txn is None:
            # we have existing imported txn but has no corresponding generated txn, let's add it to danging txns
            dangling_txns[txn.file].append(txn)

    to_add = collections.defaultdict(list)
    to_update = collections.defaultdict(dict)
    for txn in generated_txns:
        if txn.id in deleted_txn_ids:
            continue
        imported_txn = imported_id_txns.get(txn.id)
        generated_file = (work_dir / txn.file).resolve()
        if imported_txn is not None and imported_txn.file.resolve() == generated_file:
            to_update[generated_file][imported_txn.lineno] = txn
        else:
            to_add[generated_file].append(txn)

    all_files = (
        frozenset(to_remove.keys())
        .union(to_add.keys())
        .union(to_update.keys())
        .union(dangling_txns)
    )
    return {
        file_path: ChangeSet(
            remove=to_remove[file_path],
            add=to_add[file_path],
            update=to_update[file_path],
            dangling=dangling_txns[file_path],
        )
        for file_path in all_files
    }


def to_parser_entry(parser: Lark, text: str, lineno: int | None = None) -> Entry:
    tree = parser.parse(text.strip())
    entries, _ = collect_entries(tree)

    if len(entries) != 1:
        raise ValueError("Expected exactly only one entry")

    entry = entries[0]

    if lineno is not None and entry.statement is not None:
        entry.statement.meta.line = lineno

    return entry


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
    if txn.tags is not None:
        columns.extend(map(lambda t: "#" + t, txn.tags))
    if txn.links is not None:
        columns.extend(map(lambda t: "^" + t, txn.links))
    line = " ".join(columns)
    import_src = None
    if txn.sources is not None:
        import_src = ":".join(txn.sources)
    extra_metadata = []
    if txn.metadata is not None:
        for item in txn.metadata:
            if item.name in frozenset(
                [constants.IMPORT_ID_KEY, constants.IMPORT_SRC_KEY]
            ):
                raise ValueError(
                    f"Metadata item name {item.name} is reserved for beanhub-import usage"
                )
            extra_metadata.append(f"  {item.name}: {json.dumps(item.value)}")

    return "\n".join(
        [
            line,
            f"  {constants.IMPORT_ID_KEY}: {json.dumps(txn.id)}",
            *(
                (f"  {constants.IMPORT_SRC_KEY}: {json.dumps(import_src)}",)
                if import_src is not None
                else ()
            ),
            *extra_metadata,
            *(map(posting_to_text, txn.postings)),
        ]
    )


def apply_change_set(
    tree: Lark,
    change_set: ChangeSet,
    remove_dangling: bool = False,
) -> Lark:
    if tree.data != "start":  # type: ignore
        raise ValueError("expected start as the root rule")

    parser = make_parser()

    txns_to_remove = change_set.remove
    if remove_dangling and change_set.dangling is not None:
        txns_to_remove += change_set.dangling
    lines_to_remove = [txn.lineno for txn in txns_to_remove]
    line_to_entries = {
        lineno: to_parser_entry(parser, txn_to_text(txn), lineno=lineno)
        for lineno, txn in change_set.update.items()
    }
    entries_to_add = [
        # Set a super huge lineno to the new entry statement as beancount-black sorts entries based on (date, lineno).
        # if we simply add without a proper lineno, it will make sorting unstable.
        to_parser_entry(
            parser, txn_to_text(txn), lineno=constants.ADD_ENTRY_LINENO_OFFSET + i
        )
        for i, txn in enumerate(change_set.add)
    ]

    new_tree = copy.deepcopy(tree)
    entries, tail_comments = collect_entries(new_tree)  # type: ignore

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

    def _expand_entry(entry: Entry):
        new_children.append(entry.statement)
        for metadata in entry.metadata:
            new_children.extend(metadata.comments)
            new_children.append(metadata.statement)
        for posting in entry.postings:
            new_children.extend(posting.comments)
            new_children.append(posting.statement)
            for metadata in posting.metadata:
                new_children.extend(metadata.comments)
                new_children.append(metadata.statement)

    # Expand existing entries and look up update replacements if there's one
    for entry in entries:
        if entry.type == EntryType.COMMENTS:
            new_children.extend(entry.comments)
            continue

        if entry.statement is None:
            continue

        if entry.statement.meta.line in lines_to_remove:
            # We also drop the comments
            continue

        actual_entry = line_to_entries.get(entry.statement.meta.line, entry)

        # use comments from existing entry regardless
        new_children.extend(entry.comments)
        _expand_entry(actual_entry)

    # Add new entries
    for entry in entries_to_add:
        if entry.type == EntryType.COMMENTS:
            new_children.extend(entry.comments)
            continue
        new_children.extend(entry.comments)
        _expand_entry(entry)

    if tailing_comments_entry is not None:
        new_children.extend(tailing_comments_entry.comments)

    new_tree.children = new_children  # type: ignore
    return new_tree
