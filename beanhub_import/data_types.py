import enum
import typing

from pydantic import BaseModel


class ImportBaseModel(BaseModel):
    pass


class StrExactMatch(ImportBaseModel):
    equals: str


class StrContainsMatch(ImportBaseModel):
    contains: str


class StrPrefixMatch(ImportBaseModel):
    prefix: str


class StrSuffixMatch(ImportBaseModel):
    suffix: str


StrMatch = str | StrExactMatch | StrContainsMatch | StrPrefixMatch | StrSuffixMatch


class SimpleMatchRule(ImportBaseModel):
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


MatchRule = SimpleMatchRule


@enum.unique
class ActionType(str, enum.Enum):
    add_txn = "add_txn"


class Posting(ImportBaseModel):
    # account of the posting
    account: str | None = None
    # amount of the posting
    amount: str | None = None
    # currency of the posting
    currency: str | None = None


class Transaction(ImportBaseModel):
    # the import-id for de-duplication
    id: str | None = None
    date: str | None = None
    flag: str | None = None
    narration: str | None = None
    payee: str | None = None
    postings: list[Posting] | None = None


class ActionAddTxn(ImportBaseModel):
    type: typing.Literal[ActionType.add_txn]
    file: str
    txn: Transaction


ActionType = ActionAddTxn


class SimpleFileMatch(ImportBaseModel):
    pass


class InputConfigDetails(ImportBaseModel):
    prepend_postings: list[Posting] | None = None
    appending_postings: list[Posting] | None = None


class InputConfig(ImportBaseModel):
    match: SimpleFileMatch
    config: InputConfigDetails


class OutputConfig(ImportBaseModel):
    match: SimpleFileMatch


class ImportRule(ImportBaseModel):
    match: MatchRule
    actions: list[ActionType]


class ImportDoc(ImportBaseModel):
    input_configs: list[InputConfig]
    output_configs: list[OutputConfig]
    import_rules: list[ImportRule]
