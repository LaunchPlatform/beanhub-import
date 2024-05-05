import logging
import os
import pathlib
import re
import typing

from beanhub_extract.extractors import ALL_EXTRACTORS
from beanhub_extract.utils import strip_txn_base_path

from .data_types import ImportDoc
from .data_types import SimpleFileMatch
from .data_types import StrExactMatch
from .data_types import StrRegexMatch


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
        return filepath.match(pattern)
    if isinstance(pattern, StrRegexMatch):
        return re.match(pattern.regex, str(filepath)) is not None
    elif isinstance(pattern, StrExactMatch):
        return str(filepath) == pattern.equals
    else:
        raise ValueError(f"Unexpected pattern type {type(pattern)}")


def process_imports(
    import_doc: ImportDoc, input_dir: pathlib.Path, output_dir: pathlib.Path
):
    logger = logging.getLogger(__name__)
    for filepath in walk_dir_files(input_dir):
        processed = False
        for input_config in import_doc.input_files:
            if not match_file(input_config.match, filepath):
                continue
            rel_filepath = filepath.relative_to(input_dir)
            extractor_name = input_config.config.extractor
            if extractor_name is None:
                # TODO: identify input file automatically
                pass
            else:
                extractor_cls = ALL_EXTRACTORS.get(extractor_name)
                if extractor_cls is None:
                    logger.warning(
                        "Extractor %s not found for file %s, skip",
                        extractor_name,
                        rel_filepath,
                    )
                    continue
            with filepath.open("rt") as fo:
                extractor = extractor_cls(fo)
                for transaction in extractor():
                    print(strip_txn_base_path(input_dir, transaction))
            processed = True
        if processed:
            continue
