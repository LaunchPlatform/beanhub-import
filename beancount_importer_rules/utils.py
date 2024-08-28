import dataclasses
import pathlib

from beancount_importer_rules.data_types import Transaction


def strip_base_path(
    base: pathlib.Path | pathlib.PurePath,
    filepath: str | pathlib.Path | pathlib.PurePath,
    pure_posix: bool = False,
) -> str:
    """Strip file base path (parent folder) from given file path"""
    if not isinstance(filepath, pathlib.Path):
        if pure_posix:
            filepath = pathlib.PurePosixPath(filepath)
        else:
            filepath = pathlib.Path(filepath)
    return str(filepath.relative_to(base))


def strip_txn_base_path(
    base: pathlib.Path | pathlib.PurePath,
    transaction: Transaction,
    pure_posix: bool = False,
) -> Transaction:
    """Strip file base path (parent folder) from given transaction"""
    if transaction.file is None:
        return transaction
    return Transaction(
        **(
            dataclasses.asdict(transaction)
            | dict(file=strip_base_path(base, transaction.file, pure_posix))
        )
    )
