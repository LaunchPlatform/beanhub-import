import dataclasses
import logging
import os
import pathlib
import re
import typing

from beanhub_extract.data_types import Transaction
from beanhub_extract.extractors import ALL_EXTRACTORS
from beanhub_extract.utils import strip_txn_base_path
from jinja2.sandbox import SandboxedEnvironment

from .data_types import ActionType
from .data_types import GeneratedTransaction
from .data_types import ImportDoc
from .data_types import ImportRule
from .data_types import SimpleFileMatch
from .data_types import SimpleTxnMatchRule
from .data_types import StrContainsMatch
from .data_types import StrExactMatch
from .data_types import StrMatch
from .data_types import StrPrefixMatch
from .data_types import StrRegexMatch
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
        return filepath.match(pattern)
    if isinstance(pattern, StrRegexMatch):
        return re.match(pattern.regex, str(filepath)) is not None
    elif isinstance(pattern, StrExactMatch):
        return str(filepath) == pattern.equals
    else:
        raise ValueError(f"Unexpected file match type {type(pattern)}")


def match_str(pattern: StrMatch, value: str | None) -> bool:
    if value is None:
        return False
    if isinstance(pattern, str):
        return re.match(pattern, value) is not None
    elif isinstance(pattern, StrExactMatch):
        return value == pattern.equals
    elif isinstance(pattern, StrPrefixMatch):
        return value.startswith(pattern.prefix)
    elif isinstance(pattern, StrSuffixMatch):
        return value.endswith(pattern.suffix)
    elif isinstance(pattern, StrContainsMatch):
        return pattern.contains in value
    else:
        raise ValueError(f"Unexpected str match type {type(pattern)}")


def match_transaction(txn: Transaction, rule: SimpleTxnMatchRule) -> bool:
    return all(
        match_str(getattr(rule, key), getattr(txn, key))
        for key, pattern in rule.dict().items()
        if pattern is not None
    )


def process_transaction(
    template_env: SandboxedEnvironment,
    txn: Transaction,
    import_rules: list[ImportRule],
) -> typing.Generator[GeneratedTransaction, None, None]:
    txn_ctx = dataclasses.asdict(txn)

    def render_str(value: str | None) -> str | None:
        if value is None:
            return None
        return template_env.from_string(value).render(**txn_ctx)

    for import_rule in import_rules:
        if not match_transaction(txn, import_rule.match):
            continue
        for action in import_rule.actions:
            if action.type != ActionType.add_txn:
                # we only support add txn for now
                raise ValueError(f"Unsupported action type {action.type}")

            import_id = action.txn.id
            if import_id is None:
                import_id = "{{ file }}:{{ lineno }}"

            date = action.txn.date
            if date is None:
                date = "{{ date }}"

            flag = action.txn.flag
            if flag is None:
                flag = "*"

            narration = action.txn.narration
            if narration is None:
                narration = "{{ desc | default(bank_desc) | tojson }}"

            payee = action.txn.payee

            yield GeneratedTransaction(
                file=render_str(action.file),
                id=render_str(import_id),
                date=render_str(date),
                flag=render_str(flag),
                narration=render_str(narration),
                payee=render_str(payee),
                # TODO:
                postings=[],
            )
            # TODO: handle input file config here
            # TODO: gen txn entry
            pass
        break


def process_imports(
    import_doc: ImportDoc, input_dir: pathlib.Path, output_dir: pathlib.Path
):
    logger = logging.getLogger(__name__)
    template_env = SandboxedEnvironment()
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
            logger.info(
                "Processing file %s with extractor %s", rel_filepath, extractor_name
            )
            with filepath.open("rt") as fo:
                extractor = extractor_cls(fo)
                for transaction in extractor():
                    txn = strip_txn_base_path(input_dir, transaction)
                    for generated_txn in process_transaction(
                        template_env, txn, import_doc.import_rules
                    ):
                        # TODO:
                        print(generated_txn)
            processed = True
            break
        if processed:
            continue
