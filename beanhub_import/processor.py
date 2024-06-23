import dataclasses
import logging
import os
import pathlib
import re
import typing
import uuid

from beanhub_extract.data_types import Transaction
from beanhub_extract.extractors import ALL_EXTRACTORS
from beanhub_extract.extractors import detect_extractor
from beanhub_extract.utils import strip_txn_base_path
from jinja2.sandbox import SandboxedEnvironment

from . import constants
from .data_types import ActionType
from .data_types import Amount
from .data_types import DeletedTransaction
from .data_types import GeneratedPosting
from .data_types import GeneratedTransaction
from .data_types import ImportDoc
from .data_types import ImportRule
from .data_types import InputConfigDetails
from .data_types import MetadataItem
from .data_types import PostingTemplate
from .data_types import SimpleFileMatch
from .data_types import SimpleTxnMatchRule
from .data_types import StrContainsMatch
from .data_types import StrExactMatch
from .data_types import StrMatch
from .data_types import StrOneOfMatch
from .data_types import StrPrefixMatch
from .data_types import StrRegexMatch
from .data_types import StrSuffixMatch
from .data_types import TxnMatchVars
from .templates import make_environment


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
    elif isinstance(pattern, StrOneOfMatch):
        return value in pattern.one_of
    else:
        raise ValueError(f"Unexpected str match type {type(pattern)}")


def match_transaction(
    txn: Transaction,
    rule: SimpleTxnMatchRule,
) -> bool:
    return all(
        match_str(getattr(rule, key), getattr(txn, key))
        for key, pattern in rule.model_dump().items()
        if pattern is not None
    )


def match_transaction_with_vars(
    txn: Transaction,
    rules: list[TxnMatchVars],
    common_condition: SimpleTxnMatchRule | None = None,
) -> TxnMatchVars | None:
    for rule in rules:
        if match_transaction(txn, rule.cond) and (
            common_condition is None or match_transaction(txn, common_condition)
        ):
            return rule


def first_non_none(*values):
    return next((value for value in values if value is not None), None)


def process_transaction(
    template_env: SandboxedEnvironment,
    input_config: InputConfigDetails,
    import_rules: list[ImportRule],
    txn: Transaction,
    omit_token: str | None = None,
    default_import_id: str | None = None,
) -> typing.Generator[GeneratedTransaction | DeletedTransaction, None, bool]:
    logger = logging.getLogger(__name__)
    txn_ctx = dataclasses.asdict(txn)
    if omit_token is None:
        omit_token = uuid.uuid4().hex
    txn_ctx["omit"] = omit_token
    default_txn = input_config.default_txn
    processed = False
    matched_vars: dict | None = None

    def render_str(value: str | None) -> str | None:
        nonlocal matched_vars
        if value is None:
            return None
        template_ctx = txn_ctx
        if matched_vars is not None:
            template_ctx |= matched_vars
        result_value = template_env.from_string(value).render(**template_ctx)
        if omit_token is not None and result_value == omit_token:
            return None
        return result_value

    def process_links_or_tags(links_or_tags: list[str] | None) -> list[str] | None:
        if links_or_tags is None:
            return
        result = list(filter(lambda x: x, [render_str(item) for item in links_or_tags]))
        if not result:
            return
        return result

    for import_rule in import_rules:
        matched_vars = None
        if isinstance(import_rule.match, list):
            matched = match_transaction_with_vars(
                txn, import_rule.match, common_condition=import_rule.common_cond
            )
            if matched is None:
                continue
            matched_vars = {
                key: template_env.from_string(value).render(**txn_ctx)
                if isinstance(value, str)
                else value
                for key, value in (matched.vars or {}).items()
            }
        else:
            if not match_transaction(txn, import_rule.match):
                continue
        for action in import_rule.actions:
            if action.type == ActionType.ignore:
                logger.debug("Ignored transaction %s:%s", txn.file, txn.lineno)
                return True

            txn_id = first_non_none(
                getattr(action.txn, "id"),
                getattr(default_txn, "id") if default_txn is not None else None,
                default_import_id,
                constants.DEFAULT_TXN_TEMPLATE["id"],
            )
            if action.type == ActionType.del_txn:
                yield DeletedTransaction(id=render_str(txn_id))
                processed = True
                continue
            if action.type != ActionType.add_txn:
                # we only support add txn for now
                raise ValueError(f"Unsupported action type {action.type}")

            template_values = {
                key: first_non_none(
                    getattr(action.txn, key),
                    getattr(default_txn, key) if default_txn is not None else None,
                    constants.DEFAULT_TXN_TEMPLATE.get(key),
                )
                for key in ("date", "flag", "narration", "payee")
            }
            template_values["id"] = txn_id

            posting_templates: list[PostingTemplate] = []
            if input_config.prepend_postings is not None:
                posting_templates.extend(input_config.prepend_postings)
            if action.txn.postings is not None:
                posting_templates.extend(action.txn.postings)
            elif default_txn is not None and default_txn.postings is not None:
                posting_templates.extend(default_txn.postings)
            if input_config.appending_postings is not None:
                posting_templates.extend(input_config.appending_postings)

            generated_tags = process_links_or_tags(action.txn.tags)
            generated_links = process_links_or_tags(action.txn.links)

            generated_metadata = []
            if action.txn.metadata is not None:
                for item in action.txn.metadata:
                    name = render_str(item.name)
                    value = render_str(item.value)
                    if not name or not value:
                        continue
                    generated_metadata.append(MetadataItem(name=name, value=value))
            if not generated_metadata:
                generated_metadata = None

            generated_postings = []
            for posting_template in posting_templates:
                amount = None
                if posting_template.amount is not None:
                    amount = Amount(
                        number=render_str(posting_template.amount.number),
                        currency=render_str(posting_template.amount.currency),
                    )
                price = None
                if posting_template.price is not None:
                    price = Amount(
                        number=render_str(posting_template.price.number),
                        currency=render_str(posting_template.price.currency),
                    )
                cost = None
                if posting_template.cost is not None:
                    cost = render_str(posting_template.cost)
                generated_postings.append(
                    GeneratedPosting(
                        account=render_str(posting_template.account),
                        amount=amount,
                        price=price,
                        cost=cost,
                    )
                )

            output_file = first_non_none(action.file, input_config.default_file)
            if output_file is None:
                logger.error(
                    "Output file not defined when generating transaction with rule %s",
                    import_rule,
                )
                raise ValueError(
                    f"Output file not defined when generating transaction with rule {import_rule}"
                )

            processed = True
            yield GeneratedTransaction(
                # We don't add line number here because sources it is going to be added as `import-src` metadata field.
                # Otherwise, the provided CSV's lineno may change every time we run import if the date order is desc and
                # there are new transactions added since then.
                sources=[txn.file],
                file=render_str(output_file),
                tags=generated_tags,
                links=generated_links,
                metadata=generated_metadata,
                postings=generated_postings,
                **{key: render_str(value) for key, value in template_values.items()},
            )
            # TODO: make it possible to generate multiple transaction by changing rule config if there's
            #       a valid use case
        break
    logger.debug(
        "No match found for transaction %s at %s:%s", txn, txn.file, txn.lineno
    )
    return processed


def process_imports(
    import_doc: ImportDoc,
    input_dir: pathlib.Path,
) -> typing.Generator[
    GeneratedTransaction | DeletedTransaction | Transaction, None, None
]:
    logger = logging.getLogger(__name__)
    template_env = make_environment()
    omit_token = uuid.uuid4().hex
    if import_doc.context is not None:
        template_env.globals.update(import_doc.context)
    for filepath in walk_dir_files(input_dir):
        for input_config in import_doc.inputs:
            if not match_file(input_config.match, filepath):
                continue
            rel_filepath = filepath.relative_to(input_dir)
            extractor_name = input_config.config.extractor
            if extractor_name is None:
                with filepath.open("rt") as fo:
                    extractor_cls = detect_extractor(fo)
                if extractor_cls is None:
                    raise ValueError(
                        f"Extractor not specified for {rel_filepath} and the extractor type cannot be automatically detected"
                    )
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
                    txn_generator = process_transaction(
                        template_env=template_env,
                        input_config=input_config.config,
                        import_rules=import_doc.imports,
                        omit_token=omit_token,
                        default_import_id=getattr(extractor, "DEFAULT_IMPORT_ID", None),
                        txn=txn,
                    )
                    txn_processed = yield from txn_generator
                    if not txn_processed:
                        yield txn
            break
