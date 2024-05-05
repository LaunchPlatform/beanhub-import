import os
import pathlib
import typing

from .data_types import ImportDoc


def walk_dir_files(
    target_dir: pathlib.Path,
) -> typing.Generator[pathlib.Path, None, None]:
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            yield pathlib.Path(root) / file


def process_imports(
    import_doc: ImportDoc, input_dir: pathlib.Path, output_dir: pathlib.Path
):
    for input_config in import_doc.input_configs:
        for root, dirs, files in os.walk(input_dir):
            pass
