import pathlib
import typing

import pytest

TEST_PACKAGE_FOLDER = pathlib.Path(__file__).parent
FIXTURE_FOLDER = TEST_PACKAGE_FOLDER / "fixtures"


@pytest.fixture
def fixtures_folder() -> pathlib.Path:
    return FIXTURE_FOLDER


@pytest.fixture
def construct_files() -> (
    typing.Callable[[pathlib.Path, typing.Dict[str, typing.Any]], None]
):
    def _construct_files(workdir: pathlib.Path, spec: typing.Dict[str, typing.Any]):
        for name, value in spec.items():
            if isinstance(value, str):
                with open(workdir / name, "wt") as fo:
                    fo.write(value)
            elif isinstance(value, dict):
                sub_dir = workdir / name
                sub_dir.mkdir()
                _construct_files(sub_dir, value)
            else:
                raise ValueError()

    return _construct_files
