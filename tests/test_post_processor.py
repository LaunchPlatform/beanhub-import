import dataclasses
import functools
import io
import pathlib

import pytest
from beancount_black.formatter import Formatter
from beancount_parser.parser import make_parser
from lark import Lark

from beanhub_import.data_types import ChangeSet
from beanhub_import.data_types import GeneratedPosting
from beanhub_import.data_types import GeneratedTransaction
from beanhub_import.data_types import ImportedTransaction
from beanhub_import.post_processor import apply_change_set
from beanhub_import.post_processor import compute_changes
from beanhub_import.post_processor import extract_imported_transactions


def strip_txn_for_compare(base_path: pathlib.Path, txn: ImportedTransaction):
    result = dataclasses.asdict(txn)
    result["file"] = str(result["file"].relative_to(base_path).as_posix())
    return result


@pytest.fixture
def parser() -> Lark:
    return make_parser()


@pytest.fixture
def formatter() -> Formatter:
    return Formatter()


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
        pytest.param([], [], {}, id="empty"),
        pytest.param(
            [
                GeneratedTransaction(
                    id="MOCK_ID",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                )
            ],
            [],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[
                        GeneratedTransaction(
                            id="MOCK_ID",
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="main.bean",
                            postings=[],
                        )
                    ],
                    update={},
                    remove=[],
                )
            },
            id="single-add",
        ),
        pytest.param(
            [
                GeneratedTransaction(
                    id="MOCK_ID",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                )
            ],
            [
                ImportedTransaction(
                    file=pathlib.Path("other.bean"), lineno=0, id="MOCK_ID"
                )
            ],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[
                        GeneratedTransaction(
                            id="MOCK_ID",
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="main.bean",
                            postings=[],
                        )
                    ],
                    update={},
                    remove=[],
                ),
                pathlib.Path("other.bean"): ChangeSet(
                    add=[],
                    update={},
                    remove=[
                        ImportedTransaction(
                            file=pathlib.Path("other.bean"), lineno=0, id="MOCK_ID"
                        )
                    ],
                ),
            },
            id="single-remove-add",
        ),
        pytest.param(
            [
                GeneratedTransaction(
                    id="MOCK_ID",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                )
            ],
            [
                ImportedTransaction(
                    file=pathlib.Path("main.bean"), lineno=0, id="MOCK_ID"
                )
            ],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[],
                    update={
                        0: GeneratedTransaction(
                            id="MOCK_ID",
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="main.bean",
                            postings=[],
                        )
                    },
                    remove=[],
                ),
            },
            id="single-update",
        ),
        pytest.param(
            [
                GeneratedTransaction(
                    id="id0",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                ),
                GeneratedTransaction(
                    id="id1",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="other.bean",
                    postings=[],
                ),
                GeneratedTransaction(
                    id="id2",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="other.bean",
                    postings=[],
                ),
            ],
            [
                ImportedTransaction(file=pathlib.Path("main.bean"), lineno=0, id="id0"),
                ImportedTransaction(file=pathlib.Path("main.bean"), lineno=1, id="id1"),
            ],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[],
                    update={
                        0: GeneratedTransaction(
                            id="id0",
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="main.bean",
                            postings=[],
                        ),
                    },
                    remove=[
                        ImportedTransaction(
                            file=pathlib.Path("main.bean"), lineno=1, id="id1"
                        ),
                    ],
                ),
                pathlib.Path("other.bean"): ChangeSet(
                    add=[
                        GeneratedTransaction(
                            id="id1",
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="other.bean",
                            postings=[],
                        ),
                        GeneratedTransaction(
                            id="id2",
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="other.bean",
                            postings=[],
                        ),
                    ],
                    update={},
                    remove=[],
                ),
            },
            id="complex",
        ),
    ],
)
def test_compute_changes(
    gen_txns: list[GeneratedTransaction],
    import_txns: list[ImportedTransaction],
    expected: dict[str, ChangeSet],
):
    assert compute_changes(gen_txns, import_txns) == expected


@pytest.mark.parametrize(
    "bean_file, change_set, expected_file",
    [
        (
            "simple.bean",
            ChangeSet(
                add=[
                    GeneratedTransaction(
                        id="id99",
                        date="2024-05-05",
                        flag="*",
                        narration="MOCK_DESC",
                        file="main.bean",
                        postings=[
                            GeneratedPosting(
                                account="Assets:Cash",
                                amount="123.45",
                                currency="USD",
                            ),
                            GeneratedPosting(
                                account="Expenses:Food",
                                amount="-123.45",
                                currency="USD",
                            ),
                        ],
                    ),
                ],
                update={
                    12: GeneratedTransaction(
                        id="id1",
                        date="2024-03-05",
                        flag="!",
                        payee="Uber Eats",
                        narration="Buy lunch",
                        file="main.bean",
                        postings=[
                            GeneratedPosting(
                                account="Assets:Cash",
                                amount="111.45",
                                currency="USD",
                            ),
                            GeneratedPosting(
                                account="Expenses:Food",
                                amount="-111.45",
                                currency="USD",
                            ),
                        ],
                    ),
                },
                remove=[
                    ImportedTransaction(
                        file=pathlib.Path("main.bean"), lineno=28, id="id3"
                    )
                ],
            ),
            "simple-expected.bean",
        )
    ],
)
def test_apply_change_sets(
    parser: Lark,
    formatter: Formatter,
    fixtures_folder: pathlib.Path,
    bean_file: str,
    change_set: ChangeSet,
    expected_file: str,
):
    bean_file_path = fixtures_folder / "post_processor" / "apply-changes" / bean_file
    expected_file_path = (
        fixtures_folder / "post_processor" / "apply-changes" / expected_file
    )
    tree = parser.parse(bean_file_path.read_text())
    new_tree = apply_change_set(tree, change_set)
    output_str = io.StringIO()
    formatter.format(new_tree, output_str)
    assert output_str.getvalue() == expected_file_path.read_text()
