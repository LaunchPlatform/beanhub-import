import pathlib
import typing

import pytest

from beanhub_import.processor import match_file
from beanhub_import.processor import SimpleFileMatch
from beanhub_import.processor import StrContainsMatch
from beanhub_import.processor import StrPrefixMatch
from beanhub_import.processor import StrSuffixMatch
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
        ("^/path/to/([0-9])+", "/path/to/0", True),
        ("^/path/to/([0-9])+", "/path/to/0123", True),
        ("^/path/to/([0-9])+", "/path/to/a0123", False),
        (Str(contains="foo"), "/path/to/foo", True),
        (StrContainsMatch(contains="foo"), "/path/to/foobar", True),
        (StrContainsMatch(contains="foo"), "/path/to/spam-foobar", True),
        (StrContainsMatch(contains="foo"), "/path/to/spam-fobar", False),
        (StrPrefixMatch(prefix="foo"), "foo.csv", True),
        (StrPrefixMatch(prefix="foo"), "foobar.csv", True),
        (StrPrefixMatch(prefix="foo"), "xfoobar.csv", False),
        (StrSuffixMatch(suffix="bar"), "foo.csv", True),
        (StrPrefixMatch(suffix="foo"), "foobar.csv", True),
        (StrPrefixMatch(prefix="foo"), "xfoobar.csv", False),
    ],
)
def test_match_file(pattern: SimpleFileMatch, path: pathlib.PurePath, expected: bool):
    assert match_file(pattern, path) == expected
