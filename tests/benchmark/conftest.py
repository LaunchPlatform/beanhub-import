import dataclasses
import os
import pathlib
import typing

import pytest

from beanhub_import.data_types import ActionAddTxn
from beanhub_import.data_types import AmountTemplate
from beanhub_import.data_types import ImportDoc
from beanhub_import.data_types import ImportRule
from beanhub_import.data_types import InputConfig
from beanhub_import.data_types import InputConfigDetails
from beanhub_import.data_types import PostingTemplate
from beanhub_import.data_types import SimpleTxnMatchRule
from beanhub_import.data_types import StrExactMatch
from beanhub_import.data_types import TransactionTemplate

MERCURY_CSV_HEADER = (
    "Date (UTC),Description,Amount,Status,Source Account,Bank Description,"
    "Reference,Note,Last Four Digits,Name On Card,Category,GL Code,"
    "Timestamp,Original Currency"
)
CHASE_CSV_HEADER = "Transaction Date,Post Date,Description,Category,Type,Amount,Memo"
CITI_CSV_HEADER = "Status,Date,Description,Debit,Credit,Member Name"

BENCHMARK_NUM_TXNS = int(os.environ.get("BENCHMARK_NUM_TXNS", "10000"))


@dataclasses.dataclass(frozen=True)
class BenchmarkBankSpec:
    dirname: str
    extractor: str
    output_file: str
    asset_account: str
    share: float


BENCHMARK_BANKS: tuple[BenchmarkBankSpec, ...] = (
    BenchmarkBankSpec(
        dirname="mercury",
        extractor="mercury",
        output_file="mercury-output.bean",
        asset_account="Assets:Bank:US:Mercury",
        share=0.4,
    ),
    BenchmarkBankSpec(
        dirname="chase",
        extractor="chase_credit_card",
        output_file="chase-output.bean",
        asset_account="Assets:Bank:US:Chase",
        share=0.3,
    ),
    BenchmarkBankSpec(
        dirname="citi",
        extractor="citi_credit_card",
        output_file="citi-output.bean",
        asset_account="Assets:Bank:US:Citi",
        share=0.3,
    ),
)


def split_txn_counts(total: int, shares: tuple[float, ...]) -> tuple[int, ...]:
    counts = [int(total * share) for share in shares]
    counts[-1] = total - sum(counts[:-1])
    return tuple(counts)


def write_mercury_csv(csv_path: pathlib.Path, num_rows: int) -> None:
    with csv_path.open("wt", encoding="utf-8") as fo:
        fo.write(MERCURY_CSV_HEADER)
        fo.write("\n")
        for i in range(num_rows):
            amount = -(i % 1000) - (i % 100) / 100
            fo.write(
                "04-17-2024,"
                f"Vendor {i},"
                f"{amount:.2f},"
                "Sent,"
                "Mercury Checking xx1234,"
                f"Bank desc {i},"
                ",,,,,,"
                "04-17-2024 21:30:40,"
                "\n"
            )


def write_chase_csv(csv_path: pathlib.Path, num_rows: int) -> None:
    with csv_path.open("wt", encoding="utf-8") as fo:
        fo.write(CHASE_CSV_HEADER)
        fo.write("\n")
        for i in range(num_rows):
            amount = -(i % 1000) - (i % 100) / 100
            fo.write(f"04/03/2024,04/05/2024,Vendor {i},Shopping,Sale,{amount:.2f},\n")


def write_citi_csv(csv_path: pathlib.Path, num_rows: int) -> None:
    with csv_path.open("wt", encoding="utf-8") as fo:
        fo.write(CITI_CSV_HEADER)
        fo.write("\n")
        for i in range(num_rows):
            amount = (i % 1000) + (i % 100) / 100
            fo.write(f"Cleared,04/17/2024,Vendor {i},{amount:.2f},,Member {i % 5},\n")


BANK_CSV_WRITERS: dict[str, typing.Callable[[pathlib.Path, int], None]] = {
    "mercury": write_mercury_csv,
    "chase": write_chase_csv,
    "citi": write_citi_csv,
}


def write_benchmark_bank_csvs(
    workdir: pathlib.Path, txn_counts: dict[str, int]
) -> None:
    for bank in BENCHMARK_BANKS:
        bank_dir = workdir / bank.dirname
        bank_dir.mkdir()
        writer = BANK_CSV_WRITERS[bank.dirname]
        writer(bank_dir / "transactions.csv", txn_counts[bank.dirname])


def make_large_import_doc() -> ImportDoc:
    return ImportDoc(
        inputs=[
            InputConfig(
                match=f"{bank.dirname}/*.csv",
                config=InputConfigDetails(
                    extractor=bank.extractor,
                    default_file=bank.output_file,
                ),
            )
            for bank in BENCHMARK_BANKS
        ],
        imports=[
            ImportRule(
                match=SimpleTxnMatchRule(
                    extractor=StrExactMatch(equals=bank.extractor),
                ),
                actions=[
                    ActionAddTxn(
                        file=bank.output_file,
                        txn=TransactionTemplate(
                            narration="{{ desc }}",
                            postings=[
                                PostingTemplate(
                                    account=bank.asset_account,
                                    amount=AmountTemplate(
                                        number="{{ amount }}",
                                        currency="{{ currency | default('USD', true) }}",
                                    ),
                                ),
                                PostingTemplate(
                                    account="Expenses",
                                    amount=AmountTemplate(
                                        number="{{ -amount }}",
                                        currency="{{ currency | default('USD', true) }}",
                                    ),
                                ),
                            ],
                        ),
                    )
                ],
            )
            for bank in BENCHMARK_BANKS
        ],
    )


@pytest.fixture(scope="session")
def benchmark_num_txns() -> int:
    return BENCHMARK_NUM_TXNS


@pytest.fixture(scope="session")
def benchmark_txn_counts(benchmark_num_txns: int) -> dict[str, int]:
    counts = split_txn_counts(
        benchmark_num_txns, tuple(bank.share for bank in BENCHMARK_BANKS)
    )
    return {bank.dirname: count for bank, count in zip(BENCHMARK_BANKS, counts)}


@pytest.fixture(scope="session")
def large_import_dir(
    tmp_path_factory, benchmark_txn_counts: dict[str, int]
) -> pathlib.Path:
    workdir = tmp_path_factory.mktemp("benchmark_import")
    write_benchmark_bank_csvs(workdir, benchmark_txn_counts)
    return workdir


@pytest.fixture(scope="session")
def large_import_doc() -> ImportDoc:
    return make_large_import_doc()
