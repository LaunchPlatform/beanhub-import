import dataclasses
import datetime
import functools
import io
import pathlib
import textwrap

import pytest
from beancount_black.formatter import Formatter
from beancount_parser.data_types import Entry
from beancount_parser.data_types import EntryType
from beancount_parser.data_types import Metadata
from beancount_parser.data_types import Posting
from beancount_parser.parser import make_parser
from lark import Lark
from lark import Token
from lark import Tree

from beanhub_import.data_types import Amount
from beanhub_import.data_types import BeancountTransaction
from beanhub_import.data_types import ChangeSet
from beanhub_import.data_types import DeletedTransaction
from beanhub_import.data_types import GeneratedPosting
from beanhub_import.data_types import GeneratedTransaction
from beanhub_import.data_types import ImportOverrideFlag
from beanhub_import.data_types import TransactionStatement
from beanhub_import.data_types import TransactionUpdate
from beanhub_import.post_processor import apply_change_set
from beanhub_import.post_processor import compute_changes
from beanhub_import.post_processor import extract_existing_transactions
from beanhub_import.post_processor import extract_txn_statement
from beanhub_import.post_processor import gen_txn_statement
from beanhub_import.post_processor import parse_override_flags
from beanhub_import.post_processor import to_parser_entry
from beanhub_import.post_processor import update_transaction


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
    "override, expected",
    [
        (
            "none",
            frozenset([ImportOverrideFlag.NONE]),
        ),
        (
            "all",
            frozenset([ImportOverrideFlag.ALL]),
        ),
        (
            "narration",
            frozenset([ImportOverrideFlag.NARRATION]),
        ),
        (
            "all,payee",
            None,
        ),
        (
            "all,none",
            None,
        ),
        (
            "none,payee",
            None,
        ),
        (
            "foo",
            None,
        ),
        (
            "",
            None,
        ),
        (
            ",,,",
            None,
        ),
    ],
)
def test_parse_override_flags(
    override: str, expected: frozenset[ImportOverrideFlag] | None
):
    assert parse_override_flags(override) == expected


@pytest.mark.parametrize(
    "text, lineno, expected",
    [
        (
            textwrap.dedent(
                """\
        2024-08-29 ! "MOCK_PAYEE" "MOCK_NARRATIVE"
            import-id: "MOCK_IMPORT_ID"
            import-src: "mock.csv"
            Assets:Cash    -100.00 USD
            Expenses:Food   100.00 USD
        """
            ),
            5,
            Entry(
                type=EntryType.TXN,
                comments=[],
                statement=Tree(
                    Token("RULE", "statement"),
                    [
                        Tree(
                            Token("RULE", "date_directive"),
                            [
                                Tree(
                                    Token("RULE", "txn"),
                                    [
                                        Token("DATE", "2024-08-29"),
                                        Token("FLAG", "!"),
                                        Token("ESCAPED_STRING", '"MOCK_PAYEE"'),
                                        Token("ESCAPED_STRING", '"MOCK_NARRATIVE"'),
                                        None,
                                    ],
                                )
                            ],
                        ),
                        None,
                    ],
                ),
                metadata=[
                    Metadata(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "metadata_item"),
                                    [
                                        Token("METADATA_KEY", "import-id"),
                                        Token("ESCAPED_STRING", '"MOCK_IMPORT_ID"'),
                                    ],
                                ),
                                None,
                            ],
                        ),
                    ),
                    Metadata(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "metadata_item"),
                                    [
                                        Token("METADATA_KEY", "import-src"),
                                        Token("ESCAPED_STRING", '"mock.csv"'),
                                    ],
                                ),
                                None,
                            ],
                        ),
                    ),
                ],
                postings=[
                    Posting(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "posting"),
                                    [
                                        Tree(
                                            Token("RULE", "detailed_posting"),
                                            [
                                                None,
                                                Token("ACCOUNT", "Assets:Cash"),
                                                Tree(
                                                    Token("RULE", "amount"),
                                                    [
                                                        Tree(
                                                            Token(
                                                                "RULE", "number_expr"
                                                            ),
                                                            [
                                                                Tree(
                                                                    Token(
                                                                        "RULE",
                                                                        "number_atom",
                                                                    ),
                                                                    [
                                                                        Token(
                                                                            "UNARY_OP",
                                                                            "-",
                                                                        ),
                                                                        Token(
                                                                            "NUMBER",
                                                                            "100.00",
                                                                        ),
                                                                    ],
                                                                )
                                                            ],
                                                        ),
                                                        Token("CURRENCY", "USD"),
                                                    ],
                                                ),
                                                None,
                                                None,
                                            ],
                                        )
                                    ],
                                ),
                                None,
                            ],
                        ),
                        metadata=[],
                    ),
                    Posting(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "posting"),
                                    [
                                        Tree(
                                            Token("RULE", "detailed_posting"),
                                            [
                                                None,
                                                Token("ACCOUNT", "Expenses:Food"),
                                                Tree(
                                                    Token("RULE", "amount"),
                                                    [
                                                        Tree(
                                                            Token(
                                                                "RULE", "number_expr"
                                                            ),
                                                            [Token("NUMBER", "100.00")],
                                                        ),
                                                        Token("CURRENCY", "USD"),
                                                    ],
                                                ),
                                                None,
                                                None,
                                            ],
                                        )
                                    ],
                                ),
                                None,
                            ],
                        ),
                        metadata=[],
                    ),
                ],
            ),
        ),
        (
            textwrap.dedent(
                """\
            2024-08-29 * "MOCK_NARRATIVE"
                import-id: "MOCK_IMPORT_ID"
                Assets:Cash    -100.00 USD
                Expenses:Food
            """
            ),
            5,
            Entry(
                type=EntryType.TXN,
                comments=[],
                statement=Tree(
                    Token("RULE", "statement"),
                    [
                        Tree(
                            Token("RULE", "date_directive"),
                            [
                                Tree(
                                    Token("RULE", "txn"),
                                    [
                                        Token("DATE", "2024-08-29"),
                                        Token("FLAG", "*"),
                                        None,
                                        Token("ESCAPED_STRING", '"MOCK_NARRATIVE"'),
                                        None,
                                    ],
                                )
                            ],
                        ),
                        None,
                    ],
                ),
                metadata=[
                    Metadata(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "metadata_item"),
                                    [
                                        Token("METADATA_KEY", "import-id"),
                                        Token("ESCAPED_STRING", '"MOCK_IMPORT_ID"'),
                                    ],
                                ),
                                None,
                            ],
                        ),
                    ),
                ],
                postings=[
                    Posting(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "posting"),
                                    [
                                        Tree(
                                            Token("RULE", "detailed_posting"),
                                            [
                                                None,
                                                Token("ACCOUNT", "Assets:Cash"),
                                                Tree(
                                                    Token("RULE", "amount"),
                                                    [
                                                        Tree(
                                                            Token(
                                                                "RULE", "number_expr"
                                                            ),
                                                            [
                                                                Tree(
                                                                    Token(
                                                                        "RULE",
                                                                        "number_atom",
                                                                    ),
                                                                    [
                                                                        Token(
                                                                            "UNARY_OP",
                                                                            "-",
                                                                        ),
                                                                        Token(
                                                                            "NUMBER",
                                                                            "100.00",
                                                                        ),
                                                                    ],
                                                                )
                                                            ],
                                                        ),
                                                        Token("CURRENCY", "USD"),
                                                    ],
                                                ),
                                                None,
                                                None,
                                            ],
                                        )
                                    ],
                                ),
                                None,
                            ],
                        ),
                        metadata=[],
                    ),
                    Posting(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "posting"),
                                    [
                                        Tree(
                                            Token("RULE", "simple_posting"),
                                            [
                                                None,
                                                Token("ACCOUNT", "Expenses:Food"),
                                            ],
                                        )
                                    ],
                                ),
                                None,
                            ],
                        ),
                        metadata=[],
                    ),
                ],
            ),
        ),
        (
            textwrap.dedent(
                """\
                2024-08-29 * "MOCK_NARRATIVE" #Hash1 #Hash2 ^Link1 ^Link2
                    import-id: "MOCK_IMPORT_ID"
                    Assets:Cash    -100.00 USD
                    Expenses:Food
                """
            ),
            5,
            Entry(
                type=EntryType.TXN,
                comments=[],
                statement=Tree(
                    Token("RULE", "statement"),
                    [
                        Tree(
                            Token("RULE", "date_directive"),
                            [
                                Tree(
                                    Token("RULE", "txn"),
                                    [
                                        Token("DATE", "2024-08-29"),
                                        Token("FLAG", "*"),
                                        None,
                                        Token("ESCAPED_STRING", '"MOCK_NARRATIVE"'),
                                        Tree(
                                            Token("RULE", "annotations"),
                                            [
                                                Token("TAG", "#Hash1"),
                                                Token("TAG", "#Hash2"),
                                                Token("LINK", "^Link1"),
                                                Token("LINK", "^Link2"),
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        ),
                        None,
                    ],
                ),
                metadata=[
                    Metadata(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "metadata_item"),
                                    [
                                        Token("METADATA_KEY", "import-id"),
                                        Token("ESCAPED_STRING", '"MOCK_IMPORT_ID"'),
                                    ],
                                ),
                                None,
                            ],
                        ),
                    ),
                ],
                postings=[
                    Posting(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "posting"),
                                    [
                                        Tree(
                                            Token("RULE", "detailed_posting"),
                                            [
                                                None,
                                                Token("ACCOUNT", "Assets:Cash"),
                                                Tree(
                                                    Token("RULE", "amount"),
                                                    [
                                                        Tree(
                                                            Token(
                                                                "RULE", "number_expr"
                                                            ),
                                                            [
                                                                Tree(
                                                                    Token(
                                                                        "RULE",
                                                                        "number_atom",
                                                                    ),
                                                                    [
                                                                        Token(
                                                                            "UNARY_OP",
                                                                            "-",
                                                                        ),
                                                                        Token(
                                                                            "NUMBER",
                                                                            "100.00",
                                                                        ),
                                                                    ],
                                                                )
                                                            ],
                                                        ),
                                                        Token("CURRENCY", "USD"),
                                                    ],
                                                ),
                                                None,
                                                None,
                                            ],
                                        )
                                    ],
                                ),
                                None,
                            ],
                        ),
                        metadata=[],
                    ),
                    Posting(
                        comments=[],
                        statement=Tree(
                            Token("RULE", "statement"),
                            [
                                Tree(
                                    Token("RULE", "posting"),
                                    [
                                        Tree(
                                            Token("RULE", "simple_posting"),
                                            [
                                                None,
                                                Token("ACCOUNT", "Expenses:Food"),
                                            ],
                                        )
                                    ],
                                ),
                                None,
                            ],
                        ),
                        metadata=[],
                    ),
                ],
            ),
        ),
    ],
)
def test_to_parser_entry(text: str, lineno: int, expected: Entry):
    parser = make_parser()
    assert to_parser_entry(parser=parser, text=text, lineno=lineno) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            textwrap.dedent(
                """\
            2024-08-29 * "MOCK_PAYEE" "MOCK_NARRATION" #Hash1 #Hash2 ^Link1 ^Link2
                import-id: "MOCK_IMPORT_ID"
                Assets:Cash    -100.00 USD
                Expenses:Food
            """
            ),
            TransactionStatement(
                date=datetime.date(2024, 8, 29),
                flag="*",
                payee="MOCK_PAYEE",
                narration="MOCK_NARRATION",
                hashtags=["#Hash1", "#Hash2"],
                links=["^Link1", "^Link2"],
            ),
        )
    ],
)
def test_extract_txn_statement(text: str, expected: TransactionStatement):
    parser = make_parser()
    entry = to_parser_entry(parser=parser, text=text, lineno=1)
    assert extract_txn_statement(entry.statement) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            textwrap.dedent(
                """\
            2024-08-29 * "MOCK_PAYEE" "MOCK_NARRATION" #Hash1 #Hash2 ^Link1 ^Link2
                import-id: "MOCK_IMPORT_ID"
                Assets:Cash    -100.00 USD
                Expenses:Food
            """
            ),
            TransactionStatement(
                date=datetime.date(2024, 8, 29),
                flag="*",
                payee="MOCK_PAYEE",
                narration="MOCK_NARRATION",
                hashtags=["#Hash1", "#Hash2"],
                links=["^Link1", "^Link2"],
            ),
        )
    ],
)
def test_gen_txn_statement(text: str, expected: TransactionStatement):
    parser = make_parser()
    entry = to_parser_entry(parser=parser, text=text, lineno=1)
    statement = extract_txn_statement(entry.statement)
    assert gen_txn_statement(statement) == entry.statement


@pytest.mark.parametrize(
    "text, transaction_update, expected",
    [
        (
            textwrap.dedent(
                """\
            2024-08-29 * "MOCK_PAYEE" "MOCK_NARRATION" #Hash1 #Hash2 ^Link1 ^Link2
                import-id: "MOCK_IMPORT_ID"
                Assets:Cash    -100.00 USD
                Expenses:Food
            """
            ),
            TransactionUpdate(
                txn=GeneratedTransaction(
                    id="MOCK_ID",
                    sources=["import-data/mock.csv"],
                    date="2024-05-05",
                    flag="*",
                    narration="NEW_DESC",
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
                override=frozenset([ImportOverrideFlag.NARRATION]),
            ),
            TransactionStatement(
                date=datetime.date(2024, 8, 29),
                flag="*",
                payee="MOCK_PAYEE",
                narration="NEW_DESC",
                hashtags=["#Hash1", "#Hash2"],
                links=["^Link1", "^Link2"],
            ),
        ),
        (
            textwrap.dedent(
                """\
                2024-08-29 * "MOCK_PAYEE" "MOCK_NARRATION" #Hash1 #Hash2 ^Link1 ^Link2
                    import-id: "MOCK_IMPORT_ID"
                    Assets:Cash    -100.00 USD
                    Expenses:Food
                """
            ),
            TransactionUpdate(
                txn=GeneratedTransaction(
                    id="MOCK_ID",
                    sources=["import-data/mock.csv"],
                    date="2024-05-05",
                    flag="!",
                    payee="NEW_PAYEE",
                    narration="NEW_DESC",
                    file="main.bean",
                    links=["NewLink1"],
                    tags=["NewTag1"],
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
                override=frozenset(
                    [
                        ImportOverrideFlag.DATE,
                        ImportOverrideFlag.FLAG,
                        ImportOverrideFlag.PAYEE,
                        ImportOverrideFlag.NARRATION,
                        ImportOverrideFlag.HASHTAGS,
                        ImportOverrideFlag.LINKS,
                    ]
                ),
            ),
            TransactionStatement(
                date=datetime.date(2024, 5, 5),
                flag="!",
                payee="NEW_PAYEE",
                narration="NEW_DESC",
                hashtags=["#NewTag1"],
                links=["^NewLink1"],
            ),
        ),
    ],
)
def test_update_transaction(
    text: str, transaction_update: TransactionUpdate, expected: TransactionStatement
):
    parser = make_parser()
    entry = to_parser_entry(parser=parser, text=text, lineno=1)
    new_entry = update_transaction(
        parser=parser, entry=entry, transaction_update=transaction_update, lineno=1
    )
    statement = extract_txn_statement(new_entry.statement)
    assert statement == expected


@pytest.mark.parametrize(
    "folder, expected",
    [
        (
            "simple-transactions",
            [
                dict(
                    file="books/2024.bean",
                    lineno=1,
                    id="id0",
                    override=frozenset(
                        [
                            ImportOverrideFlag.NARRATION,
                            ImportOverrideFlag.PAYEE,
                            ImportOverrideFlag.FLAG,
                        ]
                    ),
                ),
                dict(
                    file="books/2024.bean",
                    lineno=12,
                    id="id1",
                    override=frozenset([ImportOverrideFlag.NONE]),
                ),
                dict(file="books/2025.bean", lineno=1, id="id2", override=None),
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
                        0: TransactionUpdate(
                            txn=GeneratedTransaction(
                                id="MOCK_ID",
                                date="2024-05-05",
                                flag="*",
                                narration="MOCK_DESC",
                                file="main.bean",
                                postings=[],
                            ),
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
                    date="2024-05-05",
                    flag="*",
                    narration="MOCK_DESC",
                    file="main.bean",
                    postings=[],
                )
            ],
            [
                BeancountTransaction(
                    file=pathlib.Path("main.bean"),
                    lineno=0,
                    id="MOCK_ID",
                    override=frozenset([ImportOverrideFlag.NONE]),
                )
            ],
            [],
            {
                pathlib.Path("main.bean"): ChangeSet(
                    add=[],
                    update={
                        0: TransactionUpdate(
                            txn=GeneratedTransaction(
                                id="MOCK_ID",
                                date="2024-05-05",
                                flag="*",
                                narration="MOCK_DESC",
                                file="main.bean",
                                postings=[],
                            ),
                            override=frozenset([ImportOverrideFlag.NONE]),
                        )
                    },
                    remove=[],
                    dangling=[],
                ),
            },
            id="single-update-with-override",
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
                        0: TransactionUpdate(
                            txn=GeneratedTransaction(
                                id="id0",
                                date="2024-05-05",
                                flag="*",
                                narration="MOCK_DESC",
                                file="main.bean",
                                postings=[],
                            )
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
                        0: TransactionUpdate(
                            txn=GeneratedTransaction(
                                id="id0",
                                date="2024-05-05",
                                flag="*",
                                narration="MOCK_DESC",
                                file="main.bean",
                                postings=[],
                            )
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
            for txn in change_set.dangling
        ]
        kwargs["update"] = {
            k: TransactionUpdate(**v) for k, v in kwargs["update"].items()
        }
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
                    13: TransactionUpdate(
                        txn=GeneratedTransaction(
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
                        )
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
                    13: TransactionUpdate(
                        txn=GeneratedTransaction(
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
                        )
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
    new_tree = apply_change_set(tree, change_set, remove_dangling=remove_dangling)
    output_str = io.StringIO()
    formatter.format(new_tree, output_str)
    assert output_str.getvalue() == expected_file_path.read_text()
