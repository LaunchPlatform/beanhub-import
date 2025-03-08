import datetime
import decimal
import functools
import pathlib
import typing

import pytest
import pytz
import yaml
from beanhub_extract.data_types import Transaction
from jinja2.sandbox import SandboxedEnvironment

from beanhub_import.data_types import ActionAddTxn
from beanhub_import.data_types import ActionDelTxn
from beanhub_import.data_types import ActionIgnore
from beanhub_import.data_types import Amount
from beanhub_import.data_types import AmountTemplate
from beanhub_import.data_types import DeletedTransaction
from beanhub_import.data_types import DeleteTransactionTemplate
from beanhub_import.data_types import FilterFieldOperation
from beanhub_import.data_types import FilterOperator
from beanhub_import.data_types import FiltersAdapter
from beanhub_import.data_types import GeneratedPosting
from beanhub_import.data_types import GeneratedTransaction
from beanhub_import.data_types import ImportDoc
from beanhub_import.data_types import ImportRule
from beanhub_import.data_types import InputConfig
from beanhub_import.data_types import InputConfigDetails
from beanhub_import.data_types import MetadataItem
from beanhub_import.data_types import MetadataItemTemplate
from beanhub_import.data_types import PostingTemplate
from beanhub_import.data_types import RawFilter
from beanhub_import.data_types import RawFilterFieldOperation
from beanhub_import.data_types import SimpleFileMatch
from beanhub_import.data_types import SimpleTxnMatchRule
from beanhub_import.data_types import StrContainsMatch
from beanhub_import.data_types import StrExactMatch
from beanhub_import.data_types import StrOneOfMatch
from beanhub_import.data_types import StrPrefixMatch
from beanhub_import.data_types import StrRegexMatch
from beanhub_import.data_types import StrSuffixMatch
from beanhub_import.data_types import TransactionTemplate
from beanhub_import.data_types import TxnMatchVars
from beanhub_import.data_types import UnprocessedTransaction
from beanhub_import.processor import eval_filter
from beanhub_import.processor import expand_input_loops
from beanhub_import.processor import Filter
from beanhub_import.processor import filter_transaction
from beanhub_import.processor import match_file
from beanhub_import.processor import match_str
from beanhub_import.processor import match_transaction
from beanhub_import.processor import match_transaction_with_vars
from beanhub_import.processor import process_imports
from beanhub_import.processor import process_transaction
from beanhub_import.processor import render_input_config_match
from beanhub_import.processor import RenderedInputConfig
from beanhub_import.processor import walk_dir_files
from beanhub_import.templates import make_environment


@pytest.fixture
def template_env() -> SandboxedEnvironment:
    return make_environment()


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
        (StrOneOfMatch(one_of=["Foo", "Bar"]), "Foo", True),
        (StrOneOfMatch(one_of=["Foo", "Bar"]), "Bar", True),
        (StrOneOfMatch(one_of=["Foo", "Bar"]), "Eggs", False),
        (StrOneOfMatch(one_of=["Foo", "Bar"]), "boo", False),
        (StrOneOfMatch(one_of=["Foo", "Bar"], ignore_case=True), "bar", True),
        (StrOneOfMatch(one_of=["Foo(.+)", "Bar(.+)"], regex=True), "FooBar", True),
        (StrOneOfMatch(one_of=["Foo(.+)", "Bar(.+)"], regex=True), "Foo", False),
        (StrOneOfMatch(one_of=["Foo(.+)", "Bar(.+)"], regex=True), "foo", False),
        (
            StrOneOfMatch(one_of=["Foo(.+)", "Bar(.+)"], regex=True, ignore_case=True),
            "foobar",
            True,
        ),
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
    "txn, rules, common_cond, expected",
    [
        (
            Transaction(extractor="MOCK_EXTRACTOR"),
            [
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(extractor=StrExactMatch(equals="OTHER")),
                ),
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    vars=dict(foo="bar"),
                ),
            ],
            None,
            TxnMatchVars(
                cond=SimpleTxnMatchRule(
                    extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                ),
                vars=dict(foo="bar"),
            ),
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR"),
            [
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(extractor=StrExactMatch(equals="OTHER")),
                    vars=dict(eggs="spam"),
                ),
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    vars=dict(foo="bar"),
                ),
            ],
            SimpleTxnMatchRule(payee=StrExactMatch(equals="PAYEE")),
            None,
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR", payee="PAYEE"),
            [
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(extractor=StrExactMatch(equals="OTHER")),
                    vars=dict(eggs="spam"),
                ),
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    vars=dict(foo="bar"),
                ),
            ],
            SimpleTxnMatchRule(payee=StrExactMatch(equals="PAYEE")),
            TxnMatchVars(
                cond=SimpleTxnMatchRule(
                    extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                ),
                vars=dict(foo="bar"),
            ),
        ),
        (
            Transaction(extractor="MOCK_EXTRACTOR"),
            [
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(extractor=StrExactMatch(equals="OTHER")),
                    vars=dict(eggs="spam"),
                ),
                TxnMatchVars(
                    cond=SimpleTxnMatchRule(extractor=StrExactMatch(equals="NOPE")),
                    vars=dict(foo="bar"),
                ),
            ],
            None,
            None,
        ),
    ],
)
def test_match_transaction_with_vars(
    txn: Transaction,
    rules: list[TxnMatchVars],
    common_cond: SimpleTxnMatchRule | None,
    expected: TxnMatchVars,
):
    assert (
        match_transaction_with_vars(txn, rules, common_condition=common_cond)
        == expected
    )


@pytest.mark.parametrize(
    "txn, input_config, import_rules, expected, expected_result",
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
                        amount=AmountTemplate(
                            number="{{ -(amount - 5) }}",
                            currency="{{ currency }}",
                        ),
                    ),
                ],
                append_postings=[
                    PostingTemplate(
                        account="Expenses:Fees",
                        amount=AmountTemplate(
                            number="-5",
                            currency="{{ currency }}",
                        ),
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
                                        amount=AmountTemplate(
                                            number="{{ amount }}",
                                            currency="{{ currency }}",
                                        ),
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
                    sources=["mock.csv"],
                    date="2024-05-05",
                    file="MOCK_EXTRACTOR.bean",
                    flag="*",
                    narration="MOCK_DESC",
                    postings=[
                        GeneratedPosting(
                            account="Expenses:Food",
                            amount=Amount(
                                number="-118.45",
                                currency="BTC",
                            ),
                        ),
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount=Amount(
                                number="123.45",
                                currency="BTC",
                            ),
                        ),
                        GeneratedPosting(
                            account="Expenses:Fees",
                            amount=Amount(
                                number="-5",
                                currency="BTC",
                            ),
                        ),
                    ],
                )
            ],
            None,
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
                prepend_postings=[
                    PostingTemplate(
                        account="Expenses:Food",
                        amount=AmountTemplate(
                            number="{{ -(amount - 5) }}",
                            currency="{{ currency }}",
                        ),
                    ),
                ],
                append_postings=[
                    PostingTemplate(
                        account="Expenses:Fees",
                        amount=AmountTemplate(
                            number="-5",
                            currency="{{ currency }}",
                        ),
                    ),
                ],
            ),
            [
                ImportRule(
                    common_cond=SimpleTxnMatchRule(
                        source_account=StrExactMatch(equals="Foobar")
                    ),
                    match=[
                        TxnMatchVars(
                            cond=SimpleTxnMatchRule(
                                extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                            ),
                            vars=dict(foo="bar{{ 123 }}"),
                        )
                    ],
                    actions=[
                        ActionAddTxn(
                            file="{{ extractor }}.bean",
                            txn=TransactionTemplate(
                                metadata=[
                                    MetadataItemTemplate(
                                        name="var_value", value="{{ foo }}"
                                    )
                                ],
                                postings=[
                                    PostingTemplate(
                                        account="Assets:Bank:{{ source_account }}",
                                        amount=AmountTemplate(
                                            number="{{ amount }}",
                                            currency="{{ currency }}",
                                        ),
                                    ),
                                ],
                            ),
                        )
                    ],
                )
            ],
            [
                GeneratedTransaction(
                    id="mock.csv:123",
                    sources=["mock.csv"],
                    date="2024-05-05",
                    file="MOCK_EXTRACTOR.bean",
                    flag="*",
                    narration="MOCK_DESC",
                    metadata=[
                        MetadataItem(name="var_value", value="bar123"),
                    ],
                    postings=[
                        GeneratedPosting(
                            account="Expenses:Food",
                            amount=Amount(
                                number="-118.45",
                                currency="BTC",
                            ),
                        ),
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount=Amount(
                                number="123.45",
                                currency="BTC",
                            ),
                        ),
                        GeneratedPosting(
                            account="Expenses:Fees",
                            amount=Amount(
                                number="-5",
                                currency="BTC",
                            ),
                        ),
                    ],
                )
            ],
            None,
            id="match-with-vars",
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
                            amount=AmountTemplate(
                                number="{{ amount }}",
                                currency="{{ currency }}",
                            ),
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
                    sources=["mock.csv"],
                    date="2024-01-01",
                    file="MOCK_EXTRACTOR.bean",
                    flag="!",
                    narration="my-MOCK_DESC",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount=Amount(
                                number="123.45",
                                currency="BTC",
                            ),
                        ),
                    ],
                )
            ],
            None,
            id="default-values",
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
            InputConfigDetails(),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    actions=[
                        ActionAddTxn(
                            file="{{ extractor }}.bean",
                            txn=TransactionTemplate(
                                payee="{{ omit }}",
                                postings=[
                                    PostingTemplate(
                                        account="Assets:Bank:Foobar",
                                        amount=AmountTemplate(
                                            number="{{ amount }}",
                                            currency="{{ currency }}",
                                        ),
                                    ),
                                ],
                            ),
                        )
                    ],
                )
            ],
            [
                GeneratedTransaction(
                    id="mock.csv:123",
                    sources=["mock.csv"],
                    date="2024-05-05",
                    file="MOCK_EXTRACTOR.bean",
                    flag="*",
                    narration="MOCK_DESC",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount=Amount(
                                number="123.45",
                                currency="BTC",
                            ),
                        ),
                    ],
                )
            ],
            None,
            id="omit-token",
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
                prepend_postings=[
                    PostingTemplate(
                        account="Expenses:Food",
                        amount=AmountTemplate(
                            number="{{ -(amount - 5) }}",
                            currency="{{ currency }}",
                        ),
                    ),
                ],
                append_postings=[
                    PostingTemplate(
                        account="Expenses:Fees",
                        amount=AmountTemplate(
                            number="-5",
                            currency="{{ currency }}",
                        ),
                    ),
                ],
            ),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="OTHER_MOCK_EXTRACTOR")
                    ),
                    actions=[],
                )
            ],
            [],
            UnprocessedTransaction(
                txn=Transaction(
                    extractor="MOCK_EXTRACTOR",
                    file="mock.csv",
                    lineno=123,
                    desc="MOCK_DESC",
                    source_account="Foobar",
                    date=datetime.date(2024, 5, 5),
                    currency="BTC",
                    amount=decimal.Decimal("123.45"),
                ),
                import_id="mock.csv:123",
                prepending_postings=[
                    GeneratedPosting(
                        account="Expenses:Food",
                        amount=Amount(number="-118.45", currency="BTC"),
                        price=None,
                        cost=None,
                    ),
                ],
                appending_postings=[
                    GeneratedPosting(
                        account="Expenses:Food",
                        amount=Amount(number="-118.45", currency="BTC"),
                        price=None,
                        cost=None,
                    ),
                ],
            ),
            id="no-match",
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
            InputConfigDetails(),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    actions=[
                        ActionDelTxn(
                            txn=DeleteTransactionTemplate(
                                id="id-{{ file }}:{{ lineno }}"
                            )
                        )
                    ],
                )
            ],
            [
                DeletedTransaction(id="id-mock.csv:123"),
            ],
            None,
            id="delete",
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
            InputConfigDetails(),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    actions=[ActionDelTxn()],
                )
            ],
            [
                DeletedTransaction(id="mock.csv:123"),
            ],
            None,
            id="delete-with-default-template",
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
            InputConfigDetails(),
            [
                ImportRule(
                    match=SimpleTxnMatchRule(
                        extractor=StrExactMatch(equals="MOCK_EXTRACTOR")
                    ),
                    actions=[ActionIgnore()],
                )
            ],
            [],
            None,
            id="ignore",
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
            None,
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
                                        account="Expenses:Food",
                                        amount=AmountTemplate(
                                            number="{{ -amount }}",
                                            currency="{{ currency }}",
                                        ),
                                    ),
                                    PostingTemplate(
                                        account="Assets:Bank:{{ source_account }}",
                                        amount=AmountTemplate(
                                            number="{{ amount }}",
                                            currency="{{ currency }}",
                                        ),
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
                    sources=["mock.csv"],
                    date="2024-05-05",
                    file="MOCK_EXTRACTOR.bean",
                    flag="*",
                    narration="MOCK_DESC",
                    postings=[
                        GeneratedPosting(
                            account="Expenses:Food",
                            amount=Amount(
                                number="-123.45",
                                currency="BTC",
                            ),
                        ),
                        GeneratedPosting(
                            account="Assets:Bank:Foobar",
                            amount=Amount(
                                number="123.45",
                                currency="BTC",
                            ),
                        ),
                    ],
                )
            ],
            None,
            id="no-config-value",
        ),
    ],
)
def test_process_transaction(
    template_env: SandboxedEnvironment,
    input_config: InputConfigDetails | None,
    import_rules: list[ImportRule],
    txn: Transaction,
    expected: list[GeneratedTransaction],
    expected_result: UnprocessedTransaction | None,
):
    result = None

    def get_result():
        nonlocal result
        result = yield from process_transaction(
            template_env=template_env,
            input_config=input_config,
            import_rules=import_rules,
            txn=txn,
        )

    assert list(get_result()) == expected
    assert result == expected_result


@pytest.mark.parametrize(
    "match, values, expected",
    [
        (
            "import-data/connect/{{ foo }}",
            dict(foo="bar.csv"),
            "import-data/connect/bar.csv",
        ),
        (
            "import-data/connect/eggs.csv",
            dict(foo="bar.csv"),
            "import-data/connect/eggs.csv",
        ),
        (
            StrExactMatch(equals="import-data/connect/{{ foo }}"),
            dict(foo="bar.csv"),
            StrExactMatch(equals="import-data/connect/bar.csv"),
        ),
        (
            StrRegexMatch(regex="import-data/connect/{{ foo }}"),
            dict(foo="bar.csv"),
            StrRegexMatch(regex="import-data/connect/bar.csv"),
        ),
    ],
)
def test_render_input_config_match(
    template_env: SandboxedEnvironment,
    match: SimpleFileMatch,
    values: dict,
    expected: SimpleFileMatch,
):
    render_str = lambda value: template_env.from_string(value).render(values)
    assert render_input_config_match(render_str=render_str, match=match) == expected


@pytest.mark.parametrize(
    "inputs, expected",
    [
        pytest.param(
            [
                InputConfig(
                    match="import-data/connect/{{ match_path }}",
                    config=InputConfigDetails(
                        extractor="{{ src_extractor }}",
                        default_file="{{ default_file }}",
                        prepend_postings=[
                            PostingTemplate(
                                account="Expenses:Food",
                                amount=AmountTemplate(
                                    number="{{ -(amount - 5) }}",
                                    currency="{{ currency }}",
                                ),
                            ),
                        ],
                    ),
                    loop=[
                        dict(
                            match_path="bar.csv",
                            src_extractor="mercury",
                            default_file="output.bean",
                        ),
                        dict(
                            match_path="eggs.csv",
                            src_extractor="chase",
                            default_file="eggs.bean",
                        ),
                    ],
                ),
                InputConfig(
                    match="import-data/connect/other.csv",
                    config=InputConfigDetails(
                        prepend_postings=[
                            PostingTemplate(
                                account="Expenses:Other",
                                amount=AmountTemplate(
                                    number="{{ -(amount - 5) }}",
                                    currency="{{ currency }}",
                                ),
                            ),
                        ],
                    ),
                ),
            ],
            [
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/bar.csv",
                        config=InputConfigDetails(
                            extractor="mercury",
                            default_file="{{ default_file }}",
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Food",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                    values=dict(
                        match_path="bar.csv",
                        src_extractor="mercury",
                        default_file="output.bean",
                    ),
                ),
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/eggs.csv",
                        config=InputConfigDetails(
                            extractor="chase",
                            default_file="{{ default_file }}",
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Food",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                    values=dict(
                        match_path="eggs.csv",
                        src_extractor="chase",
                        default_file="eggs.bean",
                    ),
                ),
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/other.csv",
                        config=InputConfigDetails(
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Other",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                ),
            ],
            id="basic",
        ),
        pytest.param(
            [
                InputConfig(
                    match="import-data/connect/{{ match_path }}",
                    config=InputConfigDetails(
                        extractor="{{ src_extractor }}",
                        default_file="{{ default_file }}",
                        prepend_postings=[
                            PostingTemplate(
                                account="Expenses:Food",
                                amount=AmountTemplate(
                                    number="{{ -(amount - 5) }}",
                                    currency="{{ currency }}",
                                ),
                            ),
                        ],
                    ),
                    filter=[
                        RawFilterFieldOperation(
                            field="{{ field }}",
                            op="{{ op }}",
                            value="{{ value }}",
                        ),
                    ],
                    loop=[
                        dict(
                            match_path="bar.csv",
                            src_extractor="mercury",
                            default_file="output.bean",
                            field="date",
                            op=">=",
                            value="2025-01-01",
                        ),
                        dict(
                            match_path="eggs.csv",
                            src_extractor="chase",
                            default_file="eggs.bean",
                            field="lineno",
                            op="!=",
                            value="1234",
                        ),
                    ],
                ),
                InputConfig(
                    match="import-data/connect/other.csv",
                    config=InputConfigDetails(
                        prepend_postings=[
                            PostingTemplate(
                                account="Expenses:Other",
                                amount=AmountTemplate(
                                    number="{{ -(amount - 5) }}",
                                    currency="{{ currency }}",
                                ),
                            ),
                        ],
                    ),
                    filter=[
                        RawFilterFieldOperation(
                            field="mock_field",
                            op=FilterOperator.greater_equal.value,
                            value="mock_value",
                        ),
                    ],
                ),
            ],
            [
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/bar.csv",
                        config=InputConfigDetails(
                            extractor="mercury",
                            default_file="{{ default_file }}",
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Food",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                    filter=[
                        FilterFieldOperation(
                            field="date",
                            op=FilterOperator.greater_equal,
                            value="2025-01-01",
                        ),
                    ],
                    values=dict(
                        match_path="bar.csv",
                        src_extractor="mercury",
                        default_file="output.bean",
                        field="date",
                        op=">=",
                        value="2025-01-01",
                    ),
                ),
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/eggs.csv",
                        config=InputConfigDetails(
                            extractor="chase",
                            default_file="{{ default_file }}",
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Food",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                    filter=[
                        FilterFieldOperation(
                            field="lineno",
                            op=FilterOperator.not_equal,
                            value="1234",
                        ),
                    ],
                    values=dict(
                        match_path="eggs.csv",
                        src_extractor="chase",
                        default_file="eggs.bean",
                        field="lineno",
                        op="!=",
                        value="1234",
                    ),
                ),
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/other.csv",
                        config=InputConfigDetails(
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Other",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                    filter=[
                        FilterFieldOperation(
                            field="mock_field",
                            op=FilterOperator.greater_equal,
                            value="mock_value",
                        ),
                    ],
                ),
            ],
            id="filter",
        ),
        pytest.param(
            [
                InputConfig(
                    match="import-data/connect/{{ match_path }}",
                    config=InputConfigDetails(
                        extractor="{{ src_extractor | default(omit) }}",
                        default_file="{{ default_file }}",
                        prepend_postings=[
                            PostingTemplate(
                                account="Expenses:Food",
                                amount=AmountTemplate(
                                    number="{{ -(amount - 5) }}",
                                    currency="{{ currency }}",
                                ),
                            ),
                        ],
                    ),
                    loop=[
                        dict(
                            match_path="bar.csv",
                            default_file="output.bean",
                        ),
                    ],
                ),
            ],
            [
                RenderedInputConfig(
                    input_config=InputConfig(
                        match="import-data/connect/bar.csv",
                        config=InputConfigDetails(
                            default_file="{{ default_file }}",
                            prepend_postings=[
                                PostingTemplate(
                                    account="Expenses:Food",
                                    amount=AmountTemplate(
                                        number="{{ -(amount - 5) }}",
                                        currency="{{ currency }}",
                                    ),
                                ),
                            ],
                        ),
                    ),
                    values=dict(
                        match_path="bar.csv",
                        default_file="output.bean",
                    ),
                ),
            ],
            id="omit",
        ),
    ],
)
def test_expand_input_loops(
    template_env: SandboxedEnvironment,
    inputs: list[InputConfig],
    expected: list[RenderedInputConfig],
):
    omit_token = "MOCK_OMIT_TOKEN"
    assert (
        list(
            expand_input_loops(
                template_env=template_env, inputs=inputs, omit_token=omit_token
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    "values, raw_filter, expected",
    [
        pytest.param(
            dict(field="mock_field", op=">=", value="mock_value"),
            [
                RawFilterFieldOperation(
                    field="{{ field }}",
                    op="{{ op }}",
                    value="{{ value }}",
                ),
                RawFilterFieldOperation(
                    field="{{ field }}_2",
                    op="==",
                    value="{{ value }}_2",
                ),
            ],
            [
                FilterFieldOperation(
                    field="mock_field",
                    op=FilterOperator.greater_equal,
                    value="mock_value",
                ),
                FilterFieldOperation(
                    field="mock_field_2",
                    op=FilterOperator.equal,
                    value="mock_value_2",
                ),
            ],
            id="list",
        ),
        pytest.param(
            dict(
                filter=FiltersAdapter.dump_python(
                    [
                        FilterFieldOperation(
                            field="mock_field",
                            op=FilterOperator.greater_equal,
                            value="mock_value",
                        ),
                        FilterFieldOperation(
                            field="mock_field_2",
                            op=FilterOperator.equal,
                            value="mock_value_2",
                        ),
                    ],
                    mode="json",
                )
            ),
            "{{ filter }}",
            [
                FilterFieldOperation(
                    field="mock_field",
                    op=FilterOperator.greater_equal,
                    value="mock_value",
                ),
                FilterFieldOperation(
                    field="mock_field_2",
                    op=FilterOperator.equal,
                    value="mock_value_2",
                ),
            ],
            id="render-str-eval",
        ),
        pytest.param(
            dict(),
            "{{ omit }}",
            None,
            id="omit",
        ),
    ],
)
def test_eval_filter(
    template_env: SandboxedEnvironment,
    values: dict,
    raw_filter: RawFilter,
    expected: list[Filter] | None,
):
    omit_token = "MOCK_OMIT_TOKEN"
    render_str = lambda value: template_env.from_string(value).render(
        dict(omit=omit_token) | values
    )
    assert (
        eval_filter(render_str=render_str, omit_token=omit_token, raw_filter=raw_filter)
        == expected
    )


@pytest.mark.parametrize(
    "operation, txns, expected",
    [
        pytest.param(
            FilterFieldOperation(
                field="date", op=FilterOperator.greater_equal, value="2025-01-01"
            ),
            [
                Transaction(extractor="mercury", date=datetime.date(2025, 1, 1)),
                Transaction(extractor="mercury", date=datetime.date(2024, 12, 31)),
            ],
            [True, False],
            id="date-field",
        ),
        pytest.param(
            FilterFieldOperation(
                field="timestamp",
                op=FilterOperator.greater_equal,
                value="2025-01-01T12:16:00",
            ),
            [
                Transaction(
                    extractor="mercury", timestamp=datetime.datetime(2025, 1, 1, 12, 15)
                ),
                Transaction(
                    extractor="mercury", timestamp=datetime.datetime(2025, 1, 1, 12, 16)
                ),
            ],
            [False, True],
            id="datetime-field",
        ),
        pytest.param(
            FilterFieldOperation(
                field="lineno", op=FilterOperator.greater_equal, value="1234"
            ),
            [
                Transaction(extractor="mercury", lineno=1233),
                Transaction(extractor="mercury", lineno=1234),
                Transaction(extractor="mercury", lineno=1235),
            ],
            [False, True, True],
            id="int-field",
        ),
        pytest.param(
            FilterFieldOperation(
                field="extractor", op=FilterOperator.equal, value="chase"
            ),
            [
                Transaction(extractor="mercury", lineno=1233),
                Transaction(extractor="mercury", lineno=1235),
                Transaction(extractor="chase", lineno=5),
            ],
            [False, False, True],
            id="int-field",
        ),
        pytest.param(
            FilterFieldOperation(
                field="amount", op=FilterOperator.less_equal, value="12.33"
            ),
            [
                Transaction(extractor="mercury", amount=decimal.Decimal("12.34")),
                Transaction(extractor="mercury", amount=decimal.Decimal("12.33")),
            ],
            [False, True],
            id="decimal-field",
        ),
    ],
)
def test_filter_transaction(
    operation: FilterFieldOperation, txns: list[Transaction], expected: list[bool]
):
    results = list(map(functools.partial(filter_transaction, operation), txns))
    assert results == expected


@pytest.mark.parametrize(
    "folder, expected",
    [
        (
            "simple-mercury",
            [
                UnprocessedTransaction(
                    txn=Transaction(
                        extractor="mercury",
                        file="mercury.csv",
                        lineno=1,
                        reversed_lineno=-4,
                        date=datetime.date(2024, 4, 17),
                        post_date=None,
                        timestamp=datetime.datetime(
                            2024, 4, 17, 21, 30, 40, tzinfo=pytz.UTC
                        ),
                        timezone="UTC",
                        desc="GUSTO",
                        bank_desc="GUSTO; FEE 111111; Launch Platform LLC",
                        amount=decimal.Decimal("-46.00"),
                        currency="",
                        category="",
                        status="Sent",
                        source_account="Mercury Checking xx12",
                        note="",
                        reference="",
                        gl_code="",
                        name_on_card="",
                        last_four_digits="",
                        extra=None,
                    ),
                    import_id="mercury.csv:-4",
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-46.00", currency="USD"),
                            price=None,
                            cost=None,
                        ),
                    ],
                ),
                GeneratedTransaction(
                    file="output.bean",
                    sources=["mercury.csv"],
                    id="mercury.csv:-3",
                    date="2024-04-16",
                    flag="*",
                    narration="Amazon Web Services",
                    payee=None,
                    tags=["MyTag"],
                    links=["MyLink"],
                    metadata=[MetadataItem(name="meta-name", value="meta-value")],
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(
                                number="-353.63",
                                currency="USD",
                            ),
                        ),
                        GeneratedPosting(
                            account="Expenses:FooBar",
                            amount=Amount(number="353.63", currency="USD"),
                        ),
                    ],
                ),
                UnprocessedTransaction(
                    txn=Transaction(
                        extractor="mercury",
                        file="mercury.csv",
                        lineno=3,
                        reversed_lineno=-2,
                        date=datetime.date(2024, 4, 16),
                        post_date=None,
                        timestamp=datetime.datetime(
                            2024, 4, 16, 3, 24, 57, tzinfo=pytz.UTC
                        ),
                        timezone="UTC",
                        desc="Adobe",
                        bank_desc="ADOBE  *ADOBE",
                        amount=decimal.Decimal("-54.99"),
                        currency="USD",
                        category="Software",
                        status="Sent",
                        type=None,
                        source_account="Mercury Credit",
                        dest_account=None,
                        note="",
                        reference="",
                        payee=None,
                        gl_code="",
                        name_on_card="Fang-Pen Lin",
                        last_four_digits="5678",
                        extra=None,
                    ),
                    import_id="mercury.csv:-2",
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-54.99", currency="USD"),
                            price=None,
                            cost=None,
                        ),
                    ],
                ),
                UnprocessedTransaction(
                    txn=Transaction(
                        extractor="mercury",
                        file="mercury.csv",
                        lineno=4,
                        reversed_lineno=-1,
                        date=datetime.date(2024, 4, 15),
                        timestamp=datetime.datetime(
                            2024, 4, 15, 14, 35, 37, tzinfo=pytz.UTC
                        ),
                        timezone="UTC",
                        desc="Jane Doe",
                        bank_desc="Send Money transaction initiated on Mercury",
                        amount=decimal.Decimal("-1500.00"),
                        currency="",
                        category="",
                        status="Sent",
                        source_account="Mercury Checking xx1234",
                        note="",
                        reference="Profit distribution",
                        gl_code="",
                        name_on_card="",
                        last_four_digits="",
                        extra=None,
                    ),
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-1500.00", currency="USD"),
                            price=None,
                            cost=None,
                        ),
                    ],
                    import_id="mercury.csv:-1",
                ),
            ],
        ),
        (
            "auto-detect",
            [
                GeneratedTransaction(
                    file="output.bean",
                    id="mercury.csv:-1",
                    sources=["mercury.csv"],
                    date="2024-04-15",
                    flag="*",
                    narration="Jane Doe",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-1500.00", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses",
                            amount=Amount(number="1500.00", currency="USD"),
                        ),
                    ],
                ),
            ],
        ),
        (
            "input-without-config",
            [
                GeneratedTransaction(
                    file="output.bean",
                    id="mercury.csv:-1",
                    sources=["mercury.csv"],
                    date="2024-04-15",
                    flag="*",
                    narration="Jane Doe",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-1500.00", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses",
                            amount=Amount(number="1500.00", currency="USD"),
                        ),
                    ],
                ),
            ],
        ),
        (
            "input-loop",
            [
                UnprocessedTransaction(
                    import_id="chase/2024.csv:-3",
                    txn=Transaction(
                        extractor="chase_credit_card",
                        file=str(pathlib.Path("chase") / "2024.csv"),
                        lineno=1,
                        reversed_lineno=-3,
                        date=datetime.date(2024, 4, 3),
                        post_date=datetime.date(2024, 4, 5),
                        desc="APPLE.COM/BILL",
                        amount=decimal.Decimal("-1.23"),
                        category="Shopping",
                        type="Sale",
                        note="",
                    ),
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Chase",
                            amount=Amount(number="-1.23", currency="USD"),
                        )
                    ],
                ),
                GeneratedTransaction(
                    file="output.bean",
                    id="chase/2024.csv:-2",
                    sources=[str(pathlib.Path("chase") / "2024.csv")],
                    date="2024-04-02",
                    flag="*",
                    narration="Amazon web services",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Chase",
                            amount=Amount(number="-6.54", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses:AWS",
                            amount=Amount(number="6.54", currency="USD"),
                        ),
                    ],
                ),
                UnprocessedTransaction(
                    import_id="chase/2024.csv:-1",
                    txn=Transaction(
                        extractor="chase_credit_card",
                        file=str(pathlib.Path("chase") / "2024.csv"),
                        lineno=3,
                        reversed_lineno=-1,
                        date=datetime.date(2024, 4, 1),
                        post_date=datetime.date(2024, 4, 2),
                        desc="GITHUB  INC.",
                        amount=decimal.Decimal("-4.00"),
                        category="Professional Services",
                        type="Sale",
                        note="",
                    ),
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Chase",
                            amount=Amount(number="-4.00", currency="USD"),
                        )
                    ],
                ),
                UnprocessedTransaction(
                    import_id="mercury/2024.csv:-2",
                    txn=Transaction(
                        extractor="mercury",
                        file=str(pathlib.Path("mercury") / "2024.csv"),
                        lineno=1,
                        reversed_lineno=-2,
                        date=datetime.date(2024, 4, 17),
                        timestamp=datetime.datetime(
                            2024, 4, 17, 21, 30, 40, tzinfo=pytz.UTC
                        ),
                        timezone="UTC",
                        desc="GUSTO",
                        bank_desc="GUSTO; FEE 111111; Launch Platform LLC",
                        amount=decimal.Decimal("-46.00"),
                        currency="",
                        category="",
                        status="Sent",
                        source_account="Mercury Checking xx12",
                        note="",
                        reference="",
                        gl_code="",
                        name_on_card="",
                        last_four_digits="",
                    ),
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-46.00", currency="USD"),
                        )
                    ],
                ),
                GeneratedTransaction(
                    file="mercury-output.bean",
                    id="mercury/2024.csv:-1",
                    sources=[str(pathlib.Path("mercury") / "2024.csv")],
                    date="2024-04-16",
                    flag="*",
                    narration="Amazon Web Services",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-353.63", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses:AWS",
                            amount=Amount(number="353.63", currency="USD"),
                        ),
                    ],
                ),
            ],
        ),
        (
            "input-loop-filter",
            [
                UnprocessedTransaction(
                    import_id="chase/2024.csv:-3",
                    txn=Transaction(
                        extractor="chase_credit_card",
                        file=str(pathlib.Path("chase") / "2024.csv"),
                        lineno=1,
                        reversed_lineno=-3,
                        date=datetime.date(2024, 4, 3),
                        post_date=datetime.date(2024, 4, 5),
                        desc="APPLE.COM/BILL",
                        amount=decimal.Decimal("-1.23"),
                        category="Shopping",
                        type="Sale",
                        note="",
                    ),
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Chase",
                            amount=Amount(number="-1.23", currency="USD"),
                        )
                    ],
                ),
                GeneratedTransaction(
                    file="output.bean",
                    id="chase/2024.csv:-2",
                    sources=[str(pathlib.Path("chase") / "2024.csv")],
                    date="2024-04-02",
                    flag="*",
                    narration="Amazon web services",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Chase",
                            amount=Amount(number="-6.54", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses:AWS",
                            amount=Amount(number="6.54", currency="USD"),
                        ),
                    ],
                ),
                UnprocessedTransaction(
                    import_id="chase/2024.csv:-1",
                    txn=Transaction(
                        extractor="chase_credit_card",
                        file=str(pathlib.Path("chase") / "2024.csv"),
                        lineno=3,
                        reversed_lineno=-1,
                        date=datetime.date(2024, 4, 1),
                        post_date=datetime.date(2024, 4, 2),
                        desc="GITHUB  INC.",
                        amount=decimal.Decimal("-4.00"),
                        category="Professional Services",
                        type="Sale",
                        note="",
                    ),
                    prepending_postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Chase",
                            amount=Amount(number="-4.00", currency="USD"),
                        )
                    ],
                ),
                GeneratedTransaction(
                    file="mercury-output.bean",
                    id="mercury/2024.csv:-2",
                    sources=[str(pathlib.Path("mercury") / "2024.csv")],
                    date="2024-04-16",
                    flag="*",
                    narration="Amazon Web Services",
                    postings=[
                        GeneratedPosting(
                            account="Assets:Bank:US:Mercury",
                            amount=Amount(number="-353.63", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses:AWS",
                            amount=Amount(number="353.63", currency="USD"),
                        ),
                    ],
                ),
            ],
        ),
        (
            "input-filter",
            [
                GeneratedTransaction(
                    file="output.bean",
                    id="mercury.csv:-2",
                    sources=["mercury.csv"],
                    date="2024-04-16",
                    flag="*",
                    narration="Amazon Web Services",
                    postings=[
                        GeneratedPosting(
                            account="Assets:NonBank:US:Mercury",
                            amount=Amount(number="-353.63", currency="USD"),
                        ),
                        GeneratedPosting(
                            account="Expenses:AWS",
                            amount=Amount(number="353.63", currency="USD"),
                        ),
                    ],
                ),
            ],
        ),
    ],
)
def test_process_imports(
    fixtures_folder: pathlib.Path, folder: str, expected: list[GeneratedTransaction]
):
    folder_path = fixtures_folder / "processor" / folder
    with open(folder_path / "import.yaml", "rt") as fo:
        payload = yaml.safe_load(fo)
    doc = ImportDoc.model_validate(payload)
    assert list(process_imports(import_doc=doc, input_dir=folder_path)) == expected
