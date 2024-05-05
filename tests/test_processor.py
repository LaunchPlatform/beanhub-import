import datetime
import decimal
import pathlib
import typing

import pytest
from beanhub_extract.data_types import Transaction
from jinja2.sandbox import SandboxedEnvironment

from beanhub_import.data_types import ActionAddTxn
from beanhub_import.data_types import GeneratedPosting
from beanhub_import.data_types import GeneratedTransaction
from beanhub_import.data_types import ImportRule
from beanhub_import.data_types import InputConfigDetails
from beanhub_import.data_types import PostingTemplate
from beanhub_import.data_types import SimpleFileMatch
from beanhub_import.data_types import SimpleTxnMatchRule
from beanhub_import.data_types import StrContainsMatch
from beanhub_import.data_types import StrExactMatch
from beanhub_import.data_types import StrPrefixMatch
from beanhub_import.data_types import StrRegexMatch
from beanhub_import.data_types import StrSuffixMatch
from beanhub_import.data_types import TransactionTemplate
from beanhub_import.processor import match_file
from beanhub_import.processor import match_str
from beanhub_import.processor import match_transaction
from beanhub_import.processor import process_transaction
from beanhub_import.processor import walk_dir_files


@pytest.fixture
def template_env() -> SandboxedEnvironment:
    return SandboxedEnvironment()


@pytest.mark.parametrize(
    "files, expected",
    [
        (
            {
                "a": {
                    "b": {
                        "1": "hey",
                        "2": {},
                    },
                    "c": "hi there",
                },
            },
            [
                "a/b/1",
                "a/c",
            ],
        )
    ],
)
def test_walk_dir_files(
    tmp_path: pathlib.Path,
    construct_files: typing.Callable,
    files: dict,
    expected: list[pathlib.Path],
):
    construct_files(tmp_path, files)
    assert frozenset(
        p.relative_to(tmp_path) for p in walk_dir_files(tmp_path)
    ) == frozenset(map(pathlib.Path, expected))


@pytest.mark.parametrize(
    "pattern, path, expected",
    [
        ("/path/to/*/foo*.csv", "/path/to/bar/foo.csv", True),
        ("/path/to/*/foo*.csv", "/path/to/bar/foo-1234.csv", True),
        ("/path/to/*/foo*.csv", "/path/to/eggs/foo-1234.csv", True),
        ("/path/to/*/foo*.csv", "/path/to/eggs/foo.csv", True),
        ("/path/to/*/foo*.csv", "/path/from/eggs/foo.csv", False),
        ("/path/to/*/foo*.csv", "foo.csv", False),
        (StrRegexMatch(regex=r"^/path/to/([0-9]+)"), "/path/to/0", True),
        (StrRegexMatch(regex=r"^/path/to/([0-9]+)"), "/path/to/0123", True),
        (StrRegexMatch(regex=r"^/path/to/([0-9]+)"), "/path/to/a0123", False),
        (StrExactMatch(equals="foo.csv"), "foo.csv", True),
        (StrExactMatch(equals="foo.csv"), "xfoo.csv", False),
    ],
)
def test_match_file(pattern: SimpleFileMatch, path: str, expected: bool):
    assert match_file(pattern, pathlib.PurePosixPath(path)) == expected


@pytest.mark.parametrize(
    "pattern, value, expected",
    [
        ("^Foo([0-9]+)", "Foo0", True),
        ("^Foo([0-9]+)", "Foo", False),
        ("^Foo([0-9]+)", "foo0", False),
        ("^Foo([0-9]+)", "", False),
        ("^Foo([0-9]+)", None, False),
        (StrPrefixMatch(prefix="Foo"), "Foo", True),
        (StrPrefixMatch(prefix="Foo"), "Foobar", True),
        (StrPrefixMatch(prefix="Foo"), "FooBAR", True),
        (StrPrefixMatch(prefix="Foo"), "xFooBAR", False),
        (StrPrefixMatch(prefix="Foo"), "", False),
        (StrPrefixMatch(prefix="Foo"), None, False),
        (StrSuffixMatch(suffix="Bar"), "Bar", True),
        (StrSuffixMatch(suffix="Bar"), "fooBar", True),
        (StrSuffixMatch(suffix="Bar"), "FooBar", True),
        (StrSuffixMatch(suffix="Bar"), "Foobar", False),
        (StrSuffixMatch(suffix="Bar"), "FooBarx", False),
        (StrSuffixMatch(suffix="Bar"), "", False),
        (StrSuffixMatch(suffix="Bar"), None, False),
        (StrContainsMatch(contains="Foo"), "Foo", True),
        (StrContainsMatch(contains="Foo"), "prefix-Foo", True),
        (StrContainsMatch(contains="Foo"), "Foo-suffix", True),
        (StrContainsMatch(contains="Foo"), "prefix-Foo-suffix", True),
        (StrContainsMatch(contains="Foo"), "prefix-Fo-suffix", False),
        (StrContainsMatch(contains="Foo"), "", False),
        (StrContainsMatch(contains="Foo"), None, False),
    ],
)
def test_match_str(pattern: SimpleFileMatch, value: str | None, expected: bool):
    assert match_str(pattern, value) == expected


@pytest.mark.parametrize(
    "txn, rule, expected",
    [
        (
            Transaction(extractor="MOCK_EXTRACTOR"),
            SimpleTxnMatchRule(extractor=StrExactMatch(equals="MOCK_EXTRACTOR")),
            True,
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR"),
            SimpleTxnMatchRule(extractor=StrExactMatch(equals="OTHER_EXTRACTOR")),
            False,
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR", desc="MOCK_DESC"),
            SimpleTxnMatchRule(
                extractor=StrExactMatch(equals="MOCK_EXTRACTOR"),
                desc=StrExactMatch(equals="MOCK_DESC"),
            ),
            True,
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR", desc="MOCK_DESC"),
            SimpleTxnMatchRule(
                extractor=StrExactMatch(equals="MOCK_EXTRACTOR"),
                desc=StrExactMatch(equals="OTHER_DESC"),
            ),
            False,
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR", desc="MOCK_DESC"),
            SimpleTxnMatchRule(
                extractor=StrExactMatch(equals="OTHER_DESC"),
                desc=StrExactMatch(equals="MOCK_DESC"),
            ),
            False,
        ),
    ],
)
def test_match_transaction(txn: Transaction, rule: SimpleTxnMatchRule, expected: bool):
    assert match_transaction(txn, rule) == expected


@pytest.mark.parametrize(
    "txn, input_config, import_rules, expected",
    [
        pytest.param(
            Transaction(
                extractor="MOCK_EXTRACTOR",
                file="mock.csv",
                lineno=123,
                desc="MOCK_DESC",
                source_account="Foobar",
                date=datetime.date(2024, 5, 5),
                currency="BTC",
                amount=decimal.Decimal("123.45"),
            ),
            InputConfigDetails(
                prepend_postings=[
                    PostingTemplate(
                        account="Expenses:Food",
                        amount="{{ -(amount - 5) }}",
                        currency="{{ currency }}",
                    ),
                ],
                appending_postings=[
                    PostingTemplate(
                        account="Expenses:Fees",
                        amount="-5",
                        currency="{{ currency }}",
                    ),
                ],
            ),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    actions=[
                        ActionAddTxn(
                            file="{{ extractor }}.bean",
                            txn=TransactionTemplate(
                                postings=[
                                    PostingTemplate(
                                        account="Assets:Bank:{{ source_account }}",
                                        amount="{{ amount }}",
                                        currency="{{ currency }}",
                                    ),
                                ]
                            ),
                        )
                    ],
                )
            ],
            [
                GeneratedTransaction(
                    id="mock.csv:123",
                    date="2024-05-05",
                    file="MOCK_EXTRACTOR.bean",
                    flag="*",
                    narration="MOCK_DESC",
                    postings=[
                        GeneratedPosting(
                            account="Expenses:Food",
                            amount="-118.45",
                            currency="BTC",
                        ),
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount="123.45",
                            currency="BTC",
                        ),
                        GeneratedPosting(
                            account="Expenses:Fees",
                            amount="-5",
                            currency="BTC",
                        ),
                    ],
                )
            ],
            id="generic",
        ),
        pytest.param(
            Transaction(
                extractor="MOCK_EXTRACTOR",
                file="mock.csv",
                lineno=123,
                desc="MOCK_DESC",
                source_account="Foobar",
                date=datetime.date(2024, 5, 5),
                currency="BTC",
                amount=decimal.Decimal("123.45"),
            ),
            InputConfigDetails(
                default_txn=TransactionTemplate(
                    id="my-{{ file }}:{{ lineno }}",
                    date="2024-01-01",
                    flag="!",
                    narration="my-{{ desc }}",
                    postings=[
                        PostingTemplate(
                            account="Assets:Bank:{{ source_account }}",
                            amount="{{ amount }}",
                            currency="{{ currency }}",
                        ),
                    ],
                ),
            ),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    actions=[
                        ActionAddTxn(
                            file="{{ extractor }}.bean",
                            txn=TransactionTemplate(),
                        )
                    ],
                )
            ],
            [
                GeneratedTransaction(
                    id="my-mock.csv:123",
                    date="2024-01-01",
                    file="MOCK_EXTRACTOR.bean",
                    flag="!",
                    narration="my-MOCK_DESC",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount="123.45",
                            currency="BTC",
                        ),
                    ],
                )
            ],
            id="default-values",
        ),
    ],
)
def test_process_transaction(
    template_env: SandboxedEnvironment,
    input_config: InputConfigDetails,
    import_rules: list[ImportRule],
    txn: Transaction,
    expected: list[GeneratedTransaction],
):
    assert (
        list(
            process_transaction(
                template_env=template_env,
                input_config=input_config,
                import_rules=import_rules,
                txn=txn,
            )
        )
        == expected
    )
