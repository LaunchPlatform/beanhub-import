import datetime
import decimal
import pathlib
import typing

import pytest
import pytz
import yaml
from jinja2.sandbox import SandboxedEnvironment

from beancount_importer_rules.data_types import (
    ActionAddTxn,
    ActionDelTxn,
    ActionIgnore,
    ActionType,
    Amount,
    AmountTemplate,
    DeletedTransaction,
    DeleteTransactionTemplate,
    GeneratedPosting,
    GeneratedTransaction,
    ImportDoc,
    ImportRule,
    InputConfigDetails,
    MetadataItem,
    MetadataItemTemplate,
    PostingTemplate,
    SimpleFileMatch,
    SimpleTxnMatchRule,
    StrContainsMatch,
    StrExactMatch,
    StrPrefixMatch,
    StrRegexMatch,
    StrSuffixMatch,
    Transaction,
    TransactionTemplate,
    TxnMatchVars,
    UnprocessedTransaction,
)
from beancount_importer_rules.extractor import create_extractor_factory
from beancount_importer_rules.includes import resolve_includes
from beancount_importer_rules.processor import (
    match_file,
    match_str,
    match_transaction,
    match_transaction_with_vars,
    process_imports,
    process_transaction,
    walk_dir_files,
)
from beancount_importer_rules.templates import make_environment


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
    ],
)
def test_match_str(
    pattern: str | StrPrefixMatch | StrSuffixMatch | StrContainsMatch,
    value: str | None,
    expected: bool,
):
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
                            type=ActionType.add_txn,
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
                    links=[],
                    tags=[],
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
                            type=ActionType.add_txn,
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
                    links=[],
                    tags=[],
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
                            type=ActionType.add_txn,
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
                    links=[],
                    tags=[],
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
                            type=ActionType.del_txn,
                            txn=DeleteTransactionTemplate(
                                id="id-{{ file }}:{{ lineno }}"
                            ),
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
                    actions=[
                        ActionIgnore(
                            type=ActionType.ignore,
                        )
                    ],
                )
            ],
            [],
            None,
            id="ignore",
        ),
    ],
)
def test_process_transaction(
    template_env: SandboxedEnvironment,
    input_config: InputConfigDetails,
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


def test_process_transaction_generic(template_env: SandboxedEnvironment):
    """
    Test a generic transaction with no specific rules.

    Pulled this test out of the above test in order to debug it.

    Turned out that changes I made to how type safety was enforced in the
    GeneratedTransaction meant that empty link and tags resulted in
    empty lists(new behaviour) instead of None (previous behaviour).

    """
    txn = Transaction(
        extractor="MOCK_EXTRACTOR",
        file="mock.csv",
        lineno=123,
        desc="MOCK_DESC",
        source_account="Foobar",
        date=datetime.date(2024, 5, 5),
        currency="BTC",
        amount=decimal.Decimal("123.45"),
    )
    input_config = InputConfigDetails(
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
    )
    import_rules = [
        ImportRule(
            match=SimpleTxnMatchRule(extractor=StrExactMatch(equals="MOCK_EXTRACTOR")),
            actions=[
                ActionAddTxn(
                    type=ActionType.add_txn,
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
    ]
    expected = [
        GeneratedTransaction(
            id="mock.csv:123",
            sources=["mock.csv"],
            date="2024-05-05",
            file="MOCK_EXTRACTOR.bean",
            flag="*",
            narration="MOCK_DESC",
            links=[],
            tags=[],
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
    ]

    result = [
        item
        for item in process_transaction(
            template_env=template_env,
            input_config=input_config,
            import_rules=import_rules,
            txn=txn,
        )
    ]

    assert result[0].__dict__ == expected[0].__dict__


@pytest.mark.parametrize(
    "folder, expected",
    [
        (
            "simple",
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
        )
    ],
)
def test_process_imports(
    fixtures_folder: pathlib.Path, folder: str, expected: list[GeneratedTransaction]
):
    folder_path = fixtures_folder / "processor" / folder
    extractor_factory = create_extractor_factory(
        working_dir=folder_path,
    )

    with open(folder_path / "import.yaml", "rt") as fo:
        payload = yaml.safe_load(fo)

    doc = ImportDoc.model_validate(payload)

    imports = resolve_includes(workdir_path=fixtures_folder, rules=doc.imports.root)

    result = list(
        process_imports(
            context=doc.context,
            imports=imports,
            inputs=doc.inputs,
            input_dir=folder_path,
            extractor_factory=extractor_factory,
        )
    )

    assert len(result) == len(expected)
