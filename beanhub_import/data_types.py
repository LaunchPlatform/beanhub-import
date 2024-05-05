import enum
import typing

from pydantic import BaseModel


class ImportBaseModel(BaseModel):
    pass


class MatchRule(ImportBaseModel):
    pass


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


class ImportRule(ImportBaseModel):
    match: MatchRule
    actions: list[ActionType]
