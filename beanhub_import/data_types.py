import dataclasses
import enum
import pathlib
import typing

import pydantic
from pydantic import BaseModel


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
    timezone: StrMatch = None
    desc: StrMatch = None
    bank_desc: StrMatch = None
    currency: StrMatch | None = None
    category: StrMatch | None = None
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


TxnMatchRule = SimpleTxnMatchRule


@enum.unique
class ActionType(str, enum.Enum):
    add_txn = "add_txn"
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


class ActionAddTxn(ImportBaseModel):
    type: typing.Literal[ActionType.add_txn] = pydantic.Field(ActionType.add_txn)
    file: str | None = None
    txn: TransactionTemplate


class ActionIgnore(ImportBaseModel):
    type: typing.Literal[ActionType.ignore] = pydantic.Field(ActionType.ignore)


Action = ActionAddTxn | ActionIgnore


SimpleFileMatch = str | StrExactMatch | StrRegexMatch


class InputConfigDetails(ImportBaseModel):
    extractor: str | None = None
    default_file: str | None = None
    prepend_postings: list[PostingTemplate] | None = None
    appending_postings: list[PostingTemplate] | None = None
    default_txn: TransactionTemplate | None = None


class InputConfig(ImportBaseModel):
    match: SimpleFileMatch
    config: InputConfigDetails


class OutputConfig(ImportBaseModel):
    match: SimpleFileMatch


class ImportRule(ImportBaseModel):
    # Name of import rule, for users to read only
    name: str | None = None
    match: TxnMatchRule
    actions: list[Action]


class ImportDoc(ImportBaseModel):
    context: dict | None = None
    inputs: list[InputConfig]
    imports: list[ImportRule]
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
