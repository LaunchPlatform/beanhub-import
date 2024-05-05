import os
import pathlib
import re
import typing

from .data_types import ImportDoc
from .data_types import SimpleFileMatch
from .data_types import StrContainsMatch
from .data_types import StrExactMatch
from .data_types import StrPrefixMatch
from .data_types import StrSuffixMatch


def walk_dir_files(
    target_dir: pathlib.Path,
) -> typing.Generator[pathlib.Path, None, None]:
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            yield pathlib.Path(root) / file


def match_file(
    pattern: SimpleFileMatch, filepath: pathlib.Path | pathlib.PurePath
) -> bool:
    if isinstance(pattern, str):
        return re.match(pattern, str(filepath)) is not None
    elif isinstance(pattern, StrExactMatch):
        return str(filepath) == pattern.equals
    elif isinstance(pattern, StrContainsMatch):
        return pattern.contains in str(filepath)
    elif isinstance(pattern, StrPrefixMatch):
        return str(filepath).startswith(pattern.prefix)
    elif isinstance(pattern, StrSuffixMatch):
        return str(filepath).endswith(pattern.suffix)
    else:
        raise ValueError(f"Unexpected pattern type {type(pattern)}")


def process_imports(
    import_doc: ImportDoc, input_dir: pathlib.Path, output_dir: pathlib.Path
):
    for filepath in walk_dir_files(input_dir):
        for input_config in import_doc.input_configs:
            pass
