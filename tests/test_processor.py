import pathlib
import typing

import pytest

from beanhub_import.processor import match_file
from beanhub_import.processor import SimpleFileMatch
from beanhub_import.processor import StrExactMatch
from beanhub_import.processor import StrRegexMatch
from beanhub_import.processor import walk_dir_files


@pytest.mark.parametrize(
    "files, expected",
    [
        (
            {
                "a": {
                    "b": {
                        "1": "hey",
                        "2": {},
                    },
                    "c": "hi there",
                },
            },
            [
                "a/b/1",
                "a/c",
            ],
        )
    ],
)
def test_walk_dir_files(
    tmp_path: pathlib.Path,
    construct_files: typing.Callable,
    files: dict,
    expected: list[pathlib.Path],
):
    construct_files(tmp_path, files)
    assert frozenset(
        p.relative_to(tmp_path) for p in walk_dir_files(tmp_path)
    ) == frozenset(map(pathlib.Path, expected))


@pytest.mark.parametrize(
    "pattern, path, expected",
    [
        ("/path/to/*/foo*.csv", "/path/to/bar/foo.csv", True),
        ("/path/to/*/foo*.csv", "/path/to/bar/foo-1234.csv", True),
        ("/path/to/*/foo*.csv", "/path/to/eggs/foo-1234.csv", True),
        ("/path/to/*/foo*.csv", "/path/to/eggs/foo.csv", True),
        ("/path/to/*/foo*.csv", "/path/from/eggs/foo.csv", False),
        ("/path/to/*/foo*.csv", "foo.csv", False),
        (StrRegexMatch(regex=r"^/path/to/([0-9]+)"), "/path/to/0", True),
        (StrRegexMatch(regex=r"^/path/to/([0-9]+)"), "/path/to/0123", True),
        (StrRegexMatch(regex=r"^/path/to/([0-9]+)"), "/path/to/a0123", False),
        (StrExactMatch(equals="foo.csv"), "foo.csv", True),
        (StrExactMatch(equals="foo.csv"), "xfoo.csv", False),
    ],
)
def test_match_file(pattern: SimpleFileMatch, path: str, expected: bool):
    assert match_file(pattern, pathlib.PurePosixPath(path)) == expected
