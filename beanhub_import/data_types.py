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


class StrPrefixMatch(ImportBaseModel):
    prefix: str


class StrSuffixMatch(ImportBaseModel):
    suffix: str


class StrContainsMatch(ImportBaseModel):
    contains: str


StrMatch = str | StrPrefixMatch | StrSuffixMatch | StrExactMatch | StrContainsMatch


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


TxnMatchRule = SimpleTxnMatchRule


@enum.unique
class ActionType(str, enum.Enum):
    add_txn = "add_txn"


class PostingTemplate(ImportBaseModel):
    # account of the posting
    account: str | None = None
    # amount of the posting
    amount: str | None = None
    # currency of the posting
    currency: str | None = None
    # TODO: support cost / price and etc


class TransactionTemplate(ImportBaseModel):
    # the import-id for de-duplication
    id: str | None = None
    date: str | None = None
    flag: str | None = None
    narration: str | None = None
    payee: str | None = None
    postings: list[PostingTemplate] | None = None


class GeneratedPosting(ImportBaseModel):
    # account of the posting
    account: str
    # amount of the posting
    amount: str | None = None
    # currency of the posting
    currency: str | None = None
    # TODO: support cost / price and etc


class GeneratedTransaction(ImportBaseModel):
    file: str
    # the import-id for de-duplication
    id: str
    date: str
    flag: str
    narration: str
    payee: str | None = None
    postings: list[GeneratedPosting]


class ActionAddTxn(ImportBaseModel):
    type: typing.Literal[ActionType.add_txn] = pydantic.Field(ActionType.add_txn)
    file: str
    txn: TransactionTemplate


Action = ActionAddTxn


SimpleFileMatch = str | StrExactMatch | StrRegexMatch


class InputConfigDetails(ImportBaseModel):
    extractor: str | None = None
    prepend_postings: list[PostingTemplate] | None = None
    appending_postings: list[PostingTemplate] | None = None
    default_txn: TransactionTemplate | None = None


class InputConfig(ImportBaseModel):
    match: SimpleFileMatch
    config: InputConfigDetails


class OutputConfig(ImportBaseModel):
    match: SimpleFileMatch


class ImportRule(ImportBaseModel):
    match: TxnMatchRule
    actions: list[Action]


class ImportDoc(ImportBaseModel):
    inputs: list[InputConfig]
    imports: list[ImportRule]
    outputs: list[OutputConfig] | None = None


@dataclasses.dataclass(frozen=True)
class ImportedTransaction:
    file: pathlib.Path
    lineno: int
    id: str


@dataclasses.dataclass(frozen=True)
class ChangeSet:
    # list of imported transaction to remove
    remove: list[ImportedTransaction]
    # map from
    update: dict[int, GeneratedTransaction]
    # list of generated transaction to add
    add: list[GeneratedTransaction]
