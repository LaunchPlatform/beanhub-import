import pathlib

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from beanhub_import.data_types import ImportDoc
from beanhub_import.processor import ImportProcessResult
from beanhub_import.processor import process_imports


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("workers", "worker_batch_size"),
    [
        (None, 16),
        (1, 16),
        (2, 1),
        (2, 16),
        (4, 1),
        (4, 16),
        (8, 1),
        (8, 16),
        (16, 1),
        (16, 16),
    ],
)
def test_process_imports_large_csv(
    benchmark: BenchmarkFixture,
    large_import_dir: pathlib.Path,
    large_import_doc: ImportDoc,
    benchmark_num_txns: int,
    workers: int | None,
    worker_batch_size: int,
) -> None:
    def run_import() -> list[ImportProcessResult]:
        return list(
            process_imports(
                import_doc=large_import_doc,
                input_dir=large_import_dir,
                workers=workers,
                worker_batch_size=worker_batch_size,
            )
        )

    results = benchmark.pedantic(run_import, rounds=1, iterations=1)
    assert len(results) == benchmark_num_txns
