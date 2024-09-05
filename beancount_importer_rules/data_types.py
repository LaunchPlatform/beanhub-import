import dataclasses
import datetime
import decimal
import enum
import pathlib
import typing

import pydantic
from pydantic import BaseModel, RootModel


@dataclasses.dataclass(frozen=True)
class Transaction:
    extractor: str
    # the filename of import source
    file: str | None = None
    # the entry line number of the source file
    lineno: int | None = None
    # the entry line number of the source file in reverse order. comes handy for CSV files in desc datetime order
    reversed_lineno: int | None = None
    # the unique id of the transaction
    transaction_id: str | None = None
    # date of the transaction
    date: datetime.date | None = None
    # date when the transaction posted
    post_date: datetime.date | None = None
    # timestamp of the transaction
    timestamp: datetime.datetime | None = None
    # timezone of the transaction, needs to be one of timezone value supported by pytz
    timezone: str | None = None
    # description of the transaction
    desc: str | None = None
    # description of the transaction provided by the bank
    bank_desc: str | None = None
    # transaction amount
    amount: decimal.Decimal | None = None
    # ISO 4217 currency symbol
    currency: str | None = None
    # category of the transaction, like Entertainment, Shopping, etc..
    category: str | None = None
    # subcategory of the transaction, like Entertainment, Shopping, etc..
    subcategory: str | None = None
    # pending status of the transaction
    pending: bool | None = None
    # status of the transaction
    status: str | None = None
    # type of the transaction, such as Sale, Return, Debit, etc
    type: str | None = None
    # Source account of the transaction
    source_account: str | None = None
    # destination account of the transaction
    dest_account: str | None = None
    # note or memo for the transaction
    note: str | None = None
    # Reference value
    reference: str | None = None
    # Payee of the transaction
    payee: str | None = None
    # General Ledger Code
    gl_code: str | None = None
    # Name on the credit/debit card
    name_on_card: str | None = None
    # Last 4 digits of credit/debit card
    last_four_digits: str | None = None
    # All the columns not handled and put into `Transaction`'s attributes by the extractor goes here
    extra: dict | None = None


@dataclasses.dataclass
class Fingerprint:
    # the starting date of rows
    starting_date: datetime.date
    # the hash value of the first row
    first_row_hash: str


class ImportBaseModel(BaseModel):
    pass


class StrRegexMatch(ImportBaseModel):
    """

    When a simple string value is provided, regular expression matching will be used. Here's an example:

    ```YAML
    imports:
    - match:
        desc: "^DoorDash (.+)"
    ```
    """

    regex: str
    """Does the transaction field match the regular expression"""


class StrExactMatch(ImportBaseModel):
    """

    To match an exact value, one can do this:

    ```YAML
    imports:
    - match:
        desc:
        equals: "DoorDash"
    ```
    """

    equals: str
    """Does the transaction field equal the value"""


class StrOneOfMatch(ImportBaseModel):
    """
    To match values belonging to a list of values, one can do this:

    ```YAML
    imports:
    - match:
        desc:
        one_of:
            - DoorDash
            - UberEats
            - Postmate
    ```
    """

    one_of: list[str]
    """Does the transaction field match one of the values"""


class StrPrefixMatch(ImportBaseModel):
    """

    To match values with a prefix, one can do this:

    ```YAML
    imports:
    - match:
        desc:
        prefix: "DoorDash"
    ```
    """

    prefix: str
    """Does the transaction field start with the string"""


class StrSuffixMatch(ImportBaseModel):
    """

    To match values with a suffix, one can do this:

    ```YAML
    imports:
    - match:
        desc:
        suffix: "DoorDash"
    ```
    """

    suffix: str
    """Does the transaction field end with the string"""


class StrContainsMatch(ImportBaseModel):
    """

    To match values containing a string, one can do this:

    ```YAML
    imports:
    - match:
        desc:
        contains: "DoorDash"
    ```

    """

    contains: str
    """Does the transaction field contain the string"""


class DateBeforeMatch(ImportBaseModel):
    """
    To match values before a date, one can do this:

    ```YAML
    imports:
    - match:
        date_before: "2021-01-01"
        format: "%Y-%m-%d"
    ```

    """

    date_before: str
    """ The date to match before"""
    format: str
    """ The format of the date. used to parse the value date and the date to match"""


class DateAfterMatch(ImportBaseModel):
    """
    To match values after a date, one can do this:

    ```YAML
    imports:
    - match:
        date_after: "2021-01-01"
        format: "%Y-%m-%d"
    ```
    """

    date_after: str
    """ The date to match after"""
    format: str
    """ The format of the date. used to parse the value date and the date to match"""


class DateSameDayMatch(ImportBaseModel):
    """
    To match values with the same day, one can do this:

    ```YAML
    imports:
    - match:
        date_same_day: "2021-01-01"
        format: "%Y-%m-%d"
    ```
    """

    date_same_day: str
    """ The date to match on the day"""
    format: str
    """ The format of the date. used to parse the value date and the date to match"""


class DateSameMonthMatch(ImportBaseModel):
    """
    To match values with the same month, one can do this:

    ```YAML
    imports:
    - match:
        date_same_month: "2021-01-01"
        format: "%Y-%m-%d"
    ```
    """

    date_same_month: str
    """ The date to match on the month"""
    format: str
    """ The format of the date. used to parse the value date and the date to match"""


class DateSameYearMatch(ImportBaseModel):
    """
    To match values with the same year, one can do this:

    ```YAML
    imports:
    - match:
        date_same_year: "2021-01-01"
        format: "%Y-%m-%d"
    ```
    """

    date_same_year: str
    """ The date to match on the year"""
    format: str
    """ The format of the date. used to parse the value date and the date to match"""


StrMatch = (
    str
    | StrPrefixMatch
    | StrSuffixMatch
    | StrExactMatch
    | StrContainsMatch
    | StrOneOfMatch
    | DateAfterMatch
    | DateBeforeMatch
    | DateSameDayMatch
    | DateSameMonthMatch
    | DateSameYearMatch
)


class SimpleTxnMatchRule(ImportBaseModel):
    """
    The raw transactions extracted by the extractor come with many attributes. Here we list only a few from it:

    The `match` object should be a dictionary.

    The key is the transaction attribute to match, and the value is the regular expression of the target pattern to match.

    All listed attributes need to match so that a transaction will considered matched.

    Only simple matching logic is possible with the current approach.

    We will extend the matching rule to support more complex matching logic in the future, such as NOT, AND, OR operators.


    """

    extractor: StrMatch | None = None
    """
    The extractor to match. This will be produced by the Extractor.get_name() method.
    """
    file: StrMatch | None = None
    """
    The file to match. This will be the file path of the source file.

    Examples

    ```yaml
    imports:
    - match:
        file: "data/transactions.csv"
    ```

    ```yaml
    imports:
    - match:
        file:
            prefix: "data/"
    ```

    ```yaml
    imports:
    - match:
        file:
            suffix: ".csv"
    ```

    """
    date: StrMatch | None = None
    """
    The date of the transaction to match.

    Examples

    ```yaml
    imports:
    - match:
        date: "2021-01-01"
    ```

    ```yaml
    imports:
    - match:
        date:
            before: "2021-01-01"
            format: "%Y-%m-%d"
    ```

    ```yaml
    imports:
    - match:
        date:
            after: "2021-01-01"
            format: "%Y-%m-%d"
    ```

    """
    post_date: StrMatch | None = None
    """
    The post date of the transaction to match.

    Examples

    ```yaml
    imports:
    - match:
        post_date: "2021-01-01"
    ```

    ```yaml
    imports:
    - match:
        post_date:
            before: "2021-01-01"
            format: "%Y-%m-%d"
    ```

    """
    timezone: StrMatch | None = None
    """
    The timezone of the transaction to match.

    Examples

    ```yaml
    imports:
    - match:
        timezone: "America/Los_Angeles"
    ```

    """
    desc: StrMatch | None = None
    """
    The description of the transaction to match.

    Probably the most common field to match.

    Examples

    ```yaml
    imports:
    - match:
        desc: "DoorDash"
    ```

    ```yaml
    imports:
    - match:
        desc:
            prefix: "DoorDash"
    ```

    ```yaml
    imports:
    - match:
        desc:
            suffix: "DoorDash"
    ```

    ```yaml
    imports:
    - match:
        desc:
            contains: "DoorDash"
    ```

    ```yaml
    imports:
    - match:
        desc:
            one_of:
                - DoorDash
                - UberEats
                - Postmate
    ```

    """

    bank_desc: StrMatch | None = None
    """
    The bank description of the transaction to match.
    """

    currency: StrMatch | None = None
    """
    The currency of the transaction to match.
    """

    category: StrMatch | None = None
    """
    The category of the transaction to match.
    """

    subcategory: StrMatch | None = None
    """
    The subcategory of the transaction to match.
    """

    status: StrMatch | None = None
    """
    The status of the transaction to match.
    """

    type: StrMatch | None = None
    """
    The type of the transaction to match.
    """

    source_account: StrMatch | None = None
    """
    The source account of the transaction to match.
    """

    dest_account: StrMatch | None = None
    """
    The destination account of the transaction to match.
    """

    note: StrMatch | None = None
    """
    The note of the transaction to match.
    """

    reference: StrMatch | None = None
    """
    The reference of the transaction to match.
    """

    payee: StrMatch | None = None
    """
    The payee of the transaction to match.
    """

    gl_code: StrMatch | None = None
    """
    The general ledger code of the transaction to match.
    """

    name_on_card: StrMatch | None = None
    """
    The name on the card of the transaction to match.
    """

    last_four_digits: StrMatch | None = None
    """
    The last four digits of the card of the transaction to match.
    """

    transaction_id: StrMatch | None = None
    """
    The transaction id of the transaction to match.
    """


TxnMatchRule = SimpleTxnMatchRule


class TxnMatchVars(ImportBaseModel):
    """

    From time to time, you may find yourself writing similar import-matching rules with
    similar transaction templates.
    To avoid repeating yourself, you can also write multiple match conditions with their
    corresponding variables to be used by the template in the same import statement.
    For example, you can simply do the following two import statements:

    ```yaml
    imports:
    - name: PG&E Gas
        match:
        extractor:
            equals: "plaid"
        desc:
            prefix: "PGANDE WEB ONLINE "
        actions:
        - txn:
            payee: "{{ payee }}"
            narration: "Paid American Express Blue Cash Everyday"
            postings:
                - account: "Expenses:Util:Gas:PGE"
                amount:
                    number: "{{ -amount }}"
                    currency: "{{ currency | default('USD', true) }}"

    - name: Comcast
        match:
        extractor:
            equals: "plaid"
        desc: "Comcast"
        actions:
        - txn:
            payee: "{{ payee }}"
            narration: "Comcast"
            postings:
                - account: "Expenses:Util:Internet:Comcast"
                amount:
                    number: "{{ -amount }}"
                    currency: "{{ currency | default('USD', true) }}"
    ```

    With match and variables, you can write:

    ```yaml
    imports:
    - name: Household expenses
        common_cond:
        extractor:
            equals: "plaid"
        match:
        - cond:
            desc:
                prefix: "PGANDE WEB ONLINE "
            vars:
            account: "Expenses:Util:Gas:PGE"
            narration: "Paid American Express Blue Cash Everyday"
        - cond:
            desc: "Comcast"
            vars:
            account: "Expenses:Housing:Util:Internet:Comcast"
            narration: "Comcast"
        actions:
        - txn:
            payee: "{{ payee }}"
            narration: "{{ narration }}"
            postings:
                - account: "{{ account } "
                amount:
                    number: "{{ -amount }}"
                    currency: "{{ currency | default('USD', true) }}"
    ```

    The `common_cond` is the condition to meet for all the matches. Instead of a map, you define
    the match with the `cond` field and the corresponding variables with the `vars` field.
    Please note that the `vars` can also be the Jinja2 template and will rendered before
    feeding into the transaction template.
    If there are any original variables from the transaction with the same name defined in
    the `vars` field, the variables from the `vars` field always override.
    """

    cond: TxnMatchRule
    vars: dict[str, str | int | None] | None = None


@enum.unique
class ActionType(str, enum.Enum):
    add_txn = "add_txn"
    del_txn = "del_txn"
    ignore = "ignore"


class AmountTemplate(ImportBaseModel):
    number: str | None = None
    currency: str | None = None


class PostingTemplate(ImportBaseModel):
    """
    A posting transform template.

    Used to transform the raw transaction into a beancount posting.

    ```yaml
    txn:
        postings:
            - account: "Expenses:Simple"
              amount:
                  number: "{{ amount }}"
                  currency: "USD"
    ```
    """

    # account of the posting
    account: str | None = None
    """
    The account of the posting.
    """
    amount: AmountTemplate | None = None
    """
    The amount of the posting.
    """
    price: AmountTemplate | None = None
    """
    The price of the posting.
    """
    cost: str | None = None
    """
    The cost of the posting.
    """


class MetadataItemTemplate(ImportBaseModel):
    """
    A metadata list item template.

    ```yaml
    txn:
        metadata:
            - name: "import-id"
              value: "123456"
            - name: "import-src"
              value: "plaid"
    ```
    """

    name: str
    """the name of the metadata"""
    value: str
    """the value of the metadata"""


class TransactionTemplate(ImportBaseModel):
    """
    A transaction transform template.

    Used to transform the raw transaction into a beancount transaction.


    ```yaml
    txn:
        date: "2021-01-01"
        flag: "*"
        narration: "Simple Transaction"
        metadata:
            - name: "icon"
              value: "🍔"
        postings:
            - account: "Expenses:Simple"
              amount:
                  number: "{{ amount }}"
                  currency: "USD"
    ```

    results in the following beancount transaction:

    ```beancount
    2021-01-01 * "Simple Transaction"
        icon: 🍔
        Expenses:Simple                            100 USD
    ```

    """

    id: str | None = None
    """the import-id for de-duplication"""

    date: str | None = None
    """the date of the transaction"""

    flag: str | None = None
    """the flag of the transaction"""

    narration: str | None = None
    """the narration of the transaction"""

    payee: str | None = None
    """the payee of the transaction"""

    tags: list[str] | None = None
    """the tags of the transaction"""

    links: list[str] | None = None
    """the links of the transaction"""

    metadata: list[MetadataItemTemplate] | None = None
    """the metadata of the transaction"""

    postings: list[PostingTemplate] | None = None
    """the postings of the transaction"""


class DeleteTransactionTemplate(ImportBaseModel):
    """
    A transaction delete template.
    """

    id: str | None = None
    """the import-id for deleting"""


class Amount(ImportBaseModel):
    """
    A posting amount transform template.

    Used to transform the raw transaction amount into a beancount posting amount.

    Examples

    ```yaml
    amount:
        number: "{{ amount }}"
        currency: "USD"
    ```
    """

    number: str
    """
    The amount number. It can be a Jinja2 template.
    """
    currency: str
    """
    The currency of the amount.
    """


class GeneratedPosting(ImportBaseModel):
    account: str
    amount: Amount | None = None
    price: Amount | None = None
    cost: str | None = None


class MetadataItem(ImportBaseModel):
    name: str
    value: str


class GeneratedTransaction(ImportBaseModel):
    file: str
    # the `import-id` metadata field for de-duplication
    id: str
    # the `import-src` metadata field for annotating the source file(s)
    sources: list[str] | None = None
    date: str
    flag: str
    narration: str
    payee: str | None = None
    tags: list[str] | None = None
    links: list[str] | None = None
    metadata: list[MetadataItem] | None = None
    postings: list[GeneratedPosting]


class DeletedTransaction(ImportBaseModel):
    """
    represents a deleted transaction
    """

    id: str


class ActionAddTxn(ImportBaseModel):
    """
    Add a transaction to the beancount file.

    This is the default action type. If your action does not specify a type, it will be assumed to be an add transaction action.

    The following keys are available for the add transaction action:

    - `file`: output beancount file name to write the transaction to
    - `txn`: the template of the transaction to insert

    A transaction template is an object that contains the following keys:

    - `id`: the optional `import-id` to overwrite the default one. By default, `{{ file | as_posix_path }}:{{ lineno }}` will be used unless the extractor provides a default value.
    - `date`: the optional date value to overwrite the default one. By default, `{{ date }}` will be used.
    - `flag`: the optional flag value to overwrite the default one. By default, `*` will be used.
    - `narration`: the optional narration value to overwrite the default one. By default `{{ desc | default(bank_desc, true) }}` will be used.
    - `payee`: the optional payee value of the transaction.
    - `tags`: an optional list of tags for the transaction
    - `links`: an optional list of links for the transaction
    - `metadata`: an optional list of `name` and `value` objects as the metadata items for the transaction.
    - `postings`: a list of templates for postings in the transaction.

    The structure of the posting template object looks like this.

    - `account`: the account of posting
    - `amount`: the optional amount object with `number` and `currency` keys
    - `price`: the optional amount object with `number` and `currency` keys
    - `cost`: the optional template of cost spec

    """

    type: typing.Literal[ActionType.add_txn] = pydantic.Field(ActionType.add_txn)
    """
    indicates that this action is to add a transaction
    """
    file: str | None = None
    """
    Which file to add the transaction to. If not provided, the default file will be used.
    """
    txn: TransactionTemplate
    """
    The transaction transform template
    """


class ActionDelTxn(ImportBaseModel):
    """
    Delete a transaction from the beancount file.


    The following keys are available for the delete transaction action:

    - `txn`: the template of the transaction to insert

    A deleting transaction template is an object that contains the following keys:

    - `id`: the `import-id` value for ensuring transactions to be deleted. By default, `{{ file | as_posix_path }}:{{ lineno }}` will be used unless the extractor provides a default value.

    """

    type: typing.Literal[ActionType.del_txn] = pydantic.Field(ActionType.del_txn)
    """
    indicates that this action is to delete a transaction
    """
    txn: DeleteTransactionTemplate
    """
    The transaction to delete
    """


class ActionIgnore(ImportBaseModel):
    """
    Ignore the transaction.

    This prevents the transaction from being added to the beancount file.

    Sometimes, we are not interested in some transactions, but if we don't process them, you will still see them
    appear in the "unprocessed transactions" section of the report provided by our command line tool.
    To mark one transaction as processed, you can simply use the `ignore` action like this:

    ```YAML
    - name: Ignore unused entries
      match:
        extractor:
          equals: "mercury"
        desc:
          one_of:
            - Mercury Credit
            - Mercury Checking xx1234
      actions:
        - type: ignore

    """

    type: typing.Literal[ActionType.ignore] = pydantic.Field(ActionType.ignore)
    """
    indicates that this action is to ignore the transaction
    """


Action = ActionAddTxn | ActionDelTxn | ActionIgnore


SimpleFileMatch = str | StrExactMatch | StrRegexMatch
"""

Currently, we support three different modes of matching a CSV file. The first one is
the default one, glob. A simple string would make it use glob mode like this:

```YAML
inputs:
  - match: "import-data/mercury/*.csv"
```

You can also do an exact match like this:

```YAML
inputs:
- match:
    equals: "import-data/mercury/2024.csv"
```

Or, if you prefer regular expression:

```YAML
inputs:
- match:
    regex: "import-data/mercury/2([0-9]+).csv"
```

"""


class ExractorInputConfig(ImportBaseModel):
    import_path: str
    as_name: str | None = None
    date_format: str | None = None
    datetime_format: str | None = None


class InputConfigDetails(ImportBaseModel):
    """
    The input configuration details for the import rule.

    """

    extractor: ExractorInputConfig
    """
    A python import path to the extractor to use for extracting transactions from the matched file.
                The format is `package.module:extractor_class`. For example, `beancount_import_rules.extractors.plaid:PlaidExtractor`.
                Your Extractor Class should inherit from `beancount_import_rules.extractors.ExtractorBase` or
                `beancount_import_rules.extractors.ExtractorCsvBase`.
    """
    default_file: str | None = None
    """
    The default output file for generated transactions from the matched file to use if not specified
                    in the `add_txn` action.
    """
    prepend_postings: list[PostingTemplate] | None = None
    """
    Postings are to be prepended for the generated transactions from the matched file. A
                    list of posting templates as described in the [Add Transaction Action](#add-transaction-action) section.
    """
    append_postings: list[PostingTemplate] | None = None
    """
    Postings are to be appended to the generated transactions from the matched file.
                        A list of posting templates as described in the [Add Transaction Action](#add-transaction-action) section.
    """
    default_txn: TransactionTemplate | None = None
    """
    The default transaction template values to use in the generated transactions from the
                    matched file. Please see the [Add Transaction Action](#add-transaction-action) section.

    """


class InputConfig(ImportBaseModel):
    """
    The input configuration for the import rule.

    """

    match: SimpleFileMatch
    config: InputConfigDetails


class OutputConfig(ImportBaseModel):
    match: SimpleFileMatch


class ImportRule(ImportBaseModel):
    """
    An import rule to match and process transactions.

    The following keys are available for the import configuration:

    - `name`: An optional name for the user to comment on this matching rule. Currently, it has no functional purpose.
    - `match`: The rule for matching raw transactions extracted from the input CSV files. As described in the Import Match Rule Definition
    - `actions`: Decide what to do with the matched raw transactions, as the Import Action Definition describes.

    """

    name: str | None = None
    """Name of import rule, Not used, just for reference"""
    common_cond: TxnMatchRule | None = None
    """common condition to meet on top of the match rules"""
    match: TxnMatchRule | list[TxnMatchVars]
    """
    The match rule
    """
    actions: list[Action]
    """The actions to perform"""


class IncludeRule(ImportBaseModel):
    """
    Include other yaml files that contain lists of ImportRule
    """

    include: str | list[str]
    """The file path(s) to include """


class ImportList(RootModel[typing.List[ImportRule | IncludeRule]]):
    """
    The list of import rules.

    Can be a list of ImportRule or IncludeRule
    """

    pass


class ImportDoc(ImportBaseModel):
    """
    The import configuration file for beancount-importer-rules.

    Examples

            # yaml-language-server: $schema=https://raw.githubusercontent.com/zenobi-us/beancount-importer-rules/master/schema.json

            inputs:
            - match: "data/*.csv"
                config:
                extractor:
                    import_path: "beancount_importer_rules.extractor:YourExtractorClass"
                    name: "custom name for this extractor instance"
                    date_format: "%Y-%m-%d"
                    datetime_format: "%Y-%m-%d %H:%M:%S"
                default_file: "books/{{ date.year }}.bean"
                prepend_postings:
                    - account: "Assets:Bank"

            imports:
            - name: "simple"
                match:
                desc: "Simple Transaction"
                actions:
                - type: "add_txn"
                    txn:
                    date: "2021-01-01"
                    flag: "*"
                    narration: "Simple Transaction"
                    postings:
                        - account: "Expenses:Simple"
                        amount:
                            number: "{{ amount }}"
                            currency: "USD"

        You can view the [schema](https://raw.githubusercontent.com/zenobi-us/beancount-importer-rules/master/schema.json) for more details
    """

    context: dict | None = None
    """

    Context comes in handy when you need to define variables to be referenced in the template.
    As you can see in the example, we define a `routine_expenses` dictionary variable in the context.

    ```YAML
    context:
    routine_expenses:
        "Amazon Web Services":
        account: Expenses:Engineering:Servers:AWS
        Netlify:
        account: Expenses:Engineering:ServiceSubscription
        Mailchimp:
        account: Expenses:Marketing:ServiceSubscription
        Circleci:
        account: Expenses:Engineering:ServiceSubscription
        Adobe:
        account: Expenses:Design:ServiceSubscription
        Digital Ocean:
        account: Expenses:Engineering:ServiceSubscription
        Microsoft:
        account: Expenses:Office:Supplies:SoftwareAsService
        narration: "Microsoft 365 Apps for Business Subscription"
        Mercury IO Cashback:
        account: Expenses:CreditCardCashback
        narration: "Mercury IO Cashback"
        WeWork:
        account: Expenses:Office
        narration: "Virtual mailing address service fee from WeWork"
    ```

    Then, in the transaction template, we look up the dictionary to find out what narration value to use:

    ```
    "{{ routine_expenses[desc].narration | default(desc, true) | default(bank_desc, true) }}"
    ```

    """
    inputs: list[InputConfig]
    """The input rules"""
    imports: ImportList
    """The import rules"""
    outputs: list[OutputConfig] | None = None
    """The output configuration"""


@dataclasses.dataclass(frozen=True)
class BeancountTransaction:
    """
    Beancount transaction.
    """

    file: pathlib.Path
    """The beancount file path"""
    lineno: int
    """The line number of the transaction in the beancount file"""
    id: str
    """The import id of the transaction"""


@dataclasses.dataclass(frozen=True)
class ChangeSet:
    """
    Change set for beancount transactions.

    It represents the changes to be made to the beancount file.
    """

    remove: list[BeancountTransaction]
    """list of existing beancount transaction to remove"""
    update: dict[int, GeneratedTransaction]
    """map from"""
    add: list[GeneratedTransaction]
    """list of generated transaction to add"""
    dangling: list[BeancountTransaction] | None = None
    """list of existing beancount transaction with no corresponding generated transactions (dangling)"""


@dataclasses.dataclass(frozen=True)
class UnprocessedTransaction:
    """
    Unprocessed transaction.

    It represents the transaction extracted from the source file.
    """

    import_id: str
    """The import id of the transaction"""
    txn: Transaction
    """The unprocessed transaction"""
    output_file: str | None = None
    """The generated output filename if available"""
    prepending_postings: list[GeneratedPosting] | None = None
    """The generated postings to prepend to the transaction"""
    appending_postings: list[GeneratedPosting] | None = None
    """The generated postings to append to the transaction"""
