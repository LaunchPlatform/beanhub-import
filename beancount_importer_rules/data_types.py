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
    regex: str


class StrExactMatch(ImportBaseModel):
    equals: str


class StrOneOfMatch(ImportBaseModel):
    one_of: list[str]


class StrPrefixMatch(ImportBaseModel):
    prefix: str


class StrSuffixMatch(ImportBaseModel):
    suffix: str


class StrContainsMatch(ImportBaseModel):
    contains: str


StrMatch = (
    str
    | StrPrefixMatch
    | StrSuffixMatch
    | StrExactMatch
    | StrContainsMatch
    | StrOneOfMatch
)


class SimpleTxnMatchRule(ImportBaseModel):
    extractor: StrMatch | None = None
    file: StrMatch | None = None
    date: StrMatch | None = None
    post_date: StrMatch | None = None
    timezone: StrMatch | None = None
    desc: StrMatch | None = None
    bank_desc: StrMatch | None = None
    currency: StrMatch | None = None
    category: StrMatch | None = None
    subcategory: StrMatch | None = None
    status: StrMatch | None = None
    type: StrMatch | None = None
    source_account: StrMatch | None = None
    dest_account: StrMatch | None = None
    note: StrMatch | None = None
    reference: StrMatch | None = None
    payee: StrMatch | None = None
    gl_code: StrMatch | None = None
    name_on_card: StrMatch | None = None
    last_four_digits: StrMatch | None = None
    transaction_id: StrMatch | None = None


TxnMatchRule = SimpleTxnMatchRule


class TxnMatchVars(ImportBaseModel):
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
    # account of the posting
    account: str | None = None
    amount: AmountTemplate | None = None
    price: AmountTemplate | None = None
    cost: str | None = None


class MetadataItemTemplate(ImportBaseModel):
    name: str
    value: str


class TransactionTemplate(ImportBaseModel):
    # the import-id for de-duplication
    id: str | None = None
    date: str | None = None
    flag: str | None = None
    narration: str | None = None
    payee: str | None = None
    tags: list[str] | None = None
    links: list[str] | None = None
    metadata: list[MetadataItemTemplate] | None = None
    postings: list[PostingTemplate] | None = None


class DeleteTransactionTemplate(ImportBaseModel):
    # the import-id for deleting
    id: str | None = None


class Amount(ImportBaseModel):
    number: str
    currency: str


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
    id: str


class ActionAddTxn(ImportBaseModel):
    type: typing.Literal[ActionType.add_txn] = pydantic.Field(ActionType.add_txn)
    file: str | None = None
    txn: TransactionTemplate


class ActionDelTxn(ImportBaseModel):
    type: typing.Literal[ActionType.del_txn] = pydantic.Field(ActionType.del_txn)
    txn: DeleteTransactionTemplate


class ActionIgnore(ImportBaseModel):
    type: typing.Literal[ActionType.ignore] = pydantic.Field(ActionType.ignore)


Action = ActionAddTxn | ActionDelTxn | ActionIgnore


SimpleFileMatch = str | StrExactMatch | StrRegexMatch


class InputConfigDetails(ImportBaseModel):
    extractor: str | None = None
    default_file: str | None = None
    prepend_postings: list[PostingTemplate] | None = None
    # Deprecated, will be removed at some point, please use append_postings instead
    appending_postings: list[PostingTemplate] | None = None
    append_postings: list[PostingTemplate] | None = None
    default_txn: TransactionTemplate | None = None


class InputConfig(ImportBaseModel):
    match: SimpleFileMatch
    config: InputConfigDetails


class OutputConfig(ImportBaseModel):
    match: SimpleFileMatch


class ImportRule(ImportBaseModel):
    # Name of import rule, for users to read only
    name: str | None = None
    # common condition to meet on top of the match rules
    common_cond: TxnMatchRule | None = None
    match: TxnMatchRule | list[TxnMatchVars]
    actions: list[Action]


class IncludeRule(ImportBaseModel):
    include: str | list[str]


class ImportList(RootModel[typing.List[ImportRule | IncludeRule]]):
    pass


class ImportDoc(ImportBaseModel):
    context: dict | None = None
    inputs: list[InputConfig]
    imports: ImportList
    outputs: list[OutputConfig] | None = None


@dataclasses.dataclass(frozen=True)
class BeancountTransaction:
    file: pathlib.Path
    lineno: int
    id: str


@dataclasses.dataclass(frozen=True)
class ChangeSet:
    # list of existing beancount transaction to remove
    remove: list[BeancountTransaction]
    # map from
    update: dict[int, GeneratedTransaction]
    # list of generated transaction to add
    add: list[GeneratedTransaction]
    # list of existing beancount transaction with no corresponding generated transactions (dangling)
    dangling: list[BeancountTransaction] | None = None


@dataclasses.dataclass(frozen=True)
class UnprocessedTransaction:
    import_id: str
    txn: Transaction
    # The generated output filename if available
    output_file: str | None = None
    prepending_postings: list[GeneratedPosting] | None = None
    appending_postings: list[GeneratedPosting] | None = None
