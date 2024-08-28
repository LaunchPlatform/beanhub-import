import dataclasses
import functools
import io
import pathlib

import pytest
from beancount_black.formatter import Formatter
from beancount_parser.parser import make_parser
from lark import Lark

from beancount_importer_rules.data_types import (
    Amount,
    BeancountTransaction,
    ChangeSet,
    DeletedTransaction,
    GeneratedPosting,
    GeneratedTransaction,
)
from beancount_importer_rules.post_processor import (
    apply_change_set,
    compute_changes,
    extract_existing_transactions,
)


def strip_txn_for_compare(base_path: pathlib.Path, txn: BeancountTransaction):
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
                dict(file="books/2024.bean", lineno=11, id="id1"),
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
        sorted(
            list(
                map(
                    functools.partial(strip_txn_for_compare, folder_path),
                    extract_existing_transactions(
                        parser=parser, bean_file=folder_path / "main.bean"
                    ),
                )
            ),
            key=lambda item: (item["file"], item["lineno"], item["id"]),
        )
        == expected
    )


@pytest.mark.parametrize(
    "gen_txns, import_txns, del_txns, expected",
    [
        pytest.param([], [], [], {}, id="empty"),
        pytest.param(
            [
                GeneratedTransaction(
                    id="MOCK_ID",
                    sources=["import-data/mock.csv"],
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                )
            ],
            [],
            [],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[
                        GeneratedTransaction(
                            id="MOCK_ID",
                            sources=["import-data/mock.csv"],
                            date="2024-05-05",
                            flag="*",
                            narration="MOCK_DESC",
                            file="main.bean",
                            postings=[],
                        )
                    ],
                    update={},
                    remove=[],
                    dangling=[],
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
                BeancountTransaction(
                    file=pathlib.Path("other.bean"), lineno=0, id="MOCK_ID"
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
                    dangling=[],
                ),
                pathlib.Path("other.bean"): ChangeSet(
                    add=[],
                    update={},
                    remove=[
                        BeancountTransaction(
                            file=pathlib.Path("other.bean"), lineno=0, id="MOCK_ID"
                        )
                    ],
                    dangling=[],
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
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=0, id="MOCK_ID"
                )
            ],
            [],
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
                    dangling=[],
                ),
            },
            id="single-update",
        ),
        pytest.param(
            [
                GeneratedTransaction(
                    id="MOCK_ID",
                    sources=["import-data/mock.csv"],
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                )
            ],
            [
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=0, id="MOCK_ID"
                )
            ],
            [DeletedTransaction(id="MOCK_ID")],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[],
                    update={},
                    remove=[
                        BeancountTransaction(
                            file=pathlib.Path("main.bean"), lineno=0, id="MOCK_ID"
                        )
                    ],
                    dangling=[],
                )
            },
            id="single-delete",
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
                    id="id2",
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="other.bean",
                    postings=[],
                ),
            ],
            [
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=0, id="id0"
                ),
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=1, id="id1"
                ),
                BeancountTransaction(
                    file=pathlib.Path("other.bean"), lineno=2, id="id3"
                ),
            ],
            [],
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
                    remove=[],
                    dangling=[
                        BeancountTransaction(
                            file=pathlib.Path("main.bean"), lineno=1, id="id1"
                        ),
                    ],
                ),
                pathlib.Path("other.bean"): ChangeSet(
                    add=[
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
                    dangling=[
                        BeancountTransaction(
                            file=pathlib.Path("other.bean"), lineno=2, id="id3"
                        ),
                    ],
                ),
            },
            id="dangling",
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
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=0, id="id0"
                ),
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=1, id="id1"
                ),
                BeancountTransaction(
                    file=pathlib.Path("main.bean"), lineno=2, id="id-dangling"
                ),
            ],
            [],
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
                        BeancountTransaction(
                            file=pathlib.Path("main.bean"), lineno=1, id="id1"
                        ),
                    ],
                    dangling=[
                        BeancountTransaction(
                            file=pathlib.Path("main.bean"), lineno=2, id="id-dangling"
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
                    dangling=[],
                ),
            },
            id="complex",
        ),
    ],
)
def test_compute_changes(
    tmp_path: pathlib.Path,
    gen_txns: list[GeneratedTransaction],
    import_txns: list[BeancountTransaction],
    del_txns: list[DeletedTransaction],
    expected: dict[str, ChangeSet],
):
    import_txns = [
        BeancountTransaction(
            **(dataclasses.asdict(txn) | dict(file=tmp_path / txn.file))
        )
        for txn in import_txns
    ]

    def strip_imported_txn(change_set: ChangeSet) -> ChangeSet:
        kwargs = dataclasses.asdict(change_set)
        kwargs["remove"] = [
            BeancountTransaction(
                **(dataclasses.asdict(txn) | dict(file=txn.file.relative_to(tmp_path)))
            )
            for txn in change_set.remove
        ]
        kwargs["dangling"] = [
            BeancountTransaction(
                **(dataclasses.asdict(txn) | dict(file=txn.file.relative_to(tmp_path)))
            )
            for txn in change_set.dangling or []
        ]
        return ChangeSet(**kwargs)

    assert {
        key.relative_to(tmp_path): strip_imported_txn(value)
        for key, value in compute_changes(
            gen_txns,
            import_txns,
            deleted_txns=del_txns,
            work_dir=tmp_path,
        ).items()
    } == expected


@pytest.mark.parametrize(
    "bean_file, change_set, remove_dangling, expected_file",
    [
        (
            "simple.bean",
            ChangeSet(
                add=[
                    GeneratedTransaction(
                        id="id99",
                        sources=["import-data/mock.csv"],
                        date="2024-05-05",
                        flag="*",
                        narration="MOCK_DESC",
                        file="main.bean",
                        postings=[
                            GeneratedPosting(
                                account="Assets:Cash",
                                amount=Amount(number="123.45", currency="USD"),
                            ),
                            GeneratedPosting(
                                account="Expenses:Food",
                                amount=Amount(number="-123.45", currency="USD"),
                            ),
                        ],
                    ),
                ],
                update={
                    13: GeneratedTransaction(
                        id="id1",
                        date="2024-03-05",
                        flag="!",
                        payee="Uber Eats",
                        narration="Buy lunch",
                        file="main.bean",
                        postings=[
                            GeneratedPosting(
                                account="Assets:Cash",
                                amount=Amount(number="111.45", currency="USD"),
                            ),
                            GeneratedPosting(
                                account="Expenses:Food",
                                amount=Amount(number="-111.45", currency="USD"),
                            ),
                        ],
                    ),
                },
                remove=[
                    BeancountTransaction(
                        file=pathlib.Path("main.bean"), lineno=29, id="id3"
                    )
                ],
            ),
            False,
            "simple-expected.bean",
        ),
        (
            "simple.bean",
            ChangeSet(
                add=[
                    GeneratedTransaction(
                        id="id99",
                        sources=["import-data/mock.csv"],
                        date="2024-05-05",
                        flag="*",
                        narration="MOCK_DESC",
                        file="main.bean",
                        postings=[
                            GeneratedPosting(
                                account="Assets:Cash",
                                amount=Amount(number="123.45", currency="USD"),
                            ),
                            GeneratedPosting(
                                account="Expenses:Food",
                                amount=Amount(number="-123.45", currency="USD"),
                            ),
                        ],
                    ),
                ],
                update={
                    13: GeneratedTransaction(
                        id="id1",
                        date="2024-03-05",
                        flag="!",
                        payee="Uber Eats",
                        narration="Buy lunch",
                        file="main.bean",
                        postings=[
                            GeneratedPosting(
                                account="Assets:Cash",
                                amount=Amount(number="111.45", currency="USD"),
                            ),
                            GeneratedPosting(
                                account="Expenses:Food",
                                amount=Amount(number="-111.45", currency="USD"),
                            ),
                        ],
                    ),
                },
                remove=[],
                dangling=[
                    BeancountTransaction(
                        file=pathlib.Path("main.bean"), lineno=29, id="id3"
                    )
                ],
            ),
            True,
            "simple-expected.bean",
        ),
    ],
)
def test_apply_change_sets(
    parser: Lark,
    formatter: Formatter,
    fixtures_folder: pathlib.Path,
    bean_file: str,
    change_set: ChangeSet,
    remove_dangling: bool,
    expected_file: str,
):
    bean_file_path = fixtures_folder / "post_processor" / "apply-changes" / bean_file
    expected_file_path = (
        fixtures_folder / "post_processor" / "apply-changes" / expected_file
    )
    tree = parser.parse(bean_file_path.read_text())
    new_tree = apply_change_set(tree, change_set, remove_dangling=remove_dangling)  # type: ignore
    output_str = io.StringIO()
    formatter.format(new_tree, output_str)  # type: ignore
    assert output_str.getvalue() == expected_file_path.read_text()
