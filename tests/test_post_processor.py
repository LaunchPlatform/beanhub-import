import dataclasses
import functools
import pathlib

import pytest
from beancount_parser.parser import make_parser
from lark import Lark

from beanhub_import.data_types import ChangeSet
from beanhub_import.data_types import GeneratedTransaction
from beanhub_import.data_types import ImportedTransaction
from beanhub_import.post_processor import compute_changes
from beanhub_import.post_processor import extract_imported_transactions


def strip_txn_for_compare(base_path: pathlib.Path, txn: ImportedTransaction):
    result = dataclasses.asdict(txn)
    result["file"] = str(result["file"].relative_to(base_path).as_posix())
    return result


@pytest.fixture
def parser() -> Lark:
    return make_parser()


@pytest.mark.parametrize(
    "folder, expected",
    [
        (
            "simple-transactions",
            [
                dict(file="books/2024.bean", lineno=1, id="id0"),
                dict(file="books/2024.bean", lineno=10, id="id1"),
                dict(file="books/2025.bean", lineno=1, id="id2"),
            ],
        ),
    ],
)
def test_extract_imported_transactions(
    parser: Lark, fixtures_folder: pathlib.Path, folder: str, expected: list[str]
):
    folder_path = fixtures_folder / "post_processor" / folder
    assert (
        list(
            map(
                functools.partial(strip_txn_for_compare, folder_path),
                extract_imported_transactions(
                    parser=parser, bean_file=folder_path / "main.bean"
                ),
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    "gen_txns, import_txns, expected",
    [
        ([], [], {}),
    ],
)
def test_compute_changes(
    gen_txns: list[GeneratedTransaction],
    import_txns: list[ImportedTransaction],
    expected: dict[str, ChangeSet],
):
    assert compute_changes(gen_txns, import_txns) == expected
