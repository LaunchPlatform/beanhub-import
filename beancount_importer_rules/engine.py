import logging
import pathlib
import typing

import rich
import yaml
from beancount_black.formatter import Formatter
from beancount_parser.parser import make_parser
from jinja2.sandbox import SandboxedEnvironment
from lark import Lark
from rich import box
from rich.logging import RichHandler
from rich.markup import escape
from rich.padding import Padding
from rich.table import Table

from beancount_importer_rules.data_types import (
    DeletedTransaction,
    GeneratedTransaction,
    ImportDoc,
    UnprocessedTransaction,
)
from beancount_importer_rules.environment import (
    LOG_LEVEL_MAP,
    LogLevel,
)
from beancount_importer_rules.extractor import (
    ExtractorFactory,
    create_extractor_factory,
)
from beancount_importer_rules.includes import resolve_includes
from beancount_importer_rules.post_processor import (
    apply_change_set,
    compute_changes,
    extract_existing_transactions,
    txn_to_text,
)
from beancount_importer_rules.processor import process_imports
from beancount_importer_rules.templates import make_environment
from beancount_importer_rules.utils import strip_base_path

IMPORT_DOC_FILE = pathlib.Path(".beanhub") / "imports.yaml"
TABLE_HEADER_STYLE = "yellow"
TABLE_COLUMN_STYLE = "cyan"


class IProcessedTransactionsMap:
    generated_txns: list[GeneratedTransaction] = []
    deleted_txns: list[DeletedTransaction] = []
    unprocessed_txns: list[UnprocessedTransaction] = []


class ImportRuleEngine:
    log_level: LogLevel = LogLevel.INFO
    logger: logging.Logger = logging.getLogger("beanhub_cli")
    config_path: pathlib.Path
    beanfile_path: pathlib.Path
    workdir_path: pathlib.Path
    remove_dangling: bool
    template_env: SandboxedEnvironment
    extractor_factory = typing.Type[ExtractorFactory]
    parser = Lark

    def __init__(
        self,
        workdir: str,
        config_path: str,
        beanfile_path: str,
        remove_dangling: bool,
        log_level: str,
    ):
        self.workdir_path = pathlib.Path(workdir).resolve()
        self.beanfile_path = pathlib.Path(self.workdir_path / beanfile_path).resolve()
        self.config_path = pathlib.Path(self.workdir_path / config_path).resolve()
        self.remove_dangling = remove_dangling
        self.log_level = LogLevel(log_level)

        FORMAT = "%(message)s"
        logging.basicConfig(
            level=LOG_LEVEL_MAP[self.log_level],
            format=FORMAT,
            datefmt="[%X]",
            handlers=[RichHandler()],
            force=True,
        )
        self.config = self.load_config(self.config_path)
        self.template_env = make_environment()
        self.extractor_factory = create_extractor_factory(working_dir=self.workdir_path)

    def load_config(self, config_path: pathlib.Path):
        with config_path.open("rt") as fo:
            doc_payload = yaml.safe_load(fo)

            import_doc = ImportDoc.model_validate(doc_payload)

            self.logger.info(
                "Loaded import doc from [green]%s[/]",
                config_path,
                extra={"markup": True, "highlighter": None},
            )

            return import_doc

    def process_transaction(self):
        output = IProcessedTransactionsMap()
        imports = resolve_includes(
            workdir_path=self.workdir_path, rules=self.config.imports.root
        )

        transactions = process_imports(
            inputs=self.config.inputs,
            imports=imports,
            context=self.config.context,
            input_dir=self.workdir_path,
            extractor_factory=self.extractor_factory,
        )

        for txn in transactions:
            if isinstance(txn, GeneratedTransaction):
                generated_file_path = (self.workdir_path / txn.file).resolve()
                self.logger.info(
                    "Generated transaction [green]%s[/] to file [green]%s[/]",
                    txn.id,
                    strip_base_path(self.workdir_path.resolve(), generated_file_path),
                    extra={"markup": True, "highlighter": None},
                )
                output.generated_txns.append(txn)
            elif isinstance(txn, DeletedTransaction):
                self.logger.info(
                    "Deleted transaction [green]%s[/]",
                    txn.id,
                    extra={"markup": True, "highlighter": None},
                )
                output.deleted_txns.append(txn)
            elif isinstance(txn, UnprocessedTransaction):
                self.logger.info(
                    "Skipped input transaction %s at [green]%s[/]:[blue]%s[/]",
                    txn.import_id,
                    txn.txn.file,
                    txn.txn.lineno,
                    extra={"markup": True, "highlighter": None},
                )
                output.unprocessed_txns.append(txn)
            else:
                raise ValueError(f"Unexpected type {type(txn)}")

        self.logger.info("Generated %s transactions", len(output.generated_txns))
        self.logger.info("Deleted %s transactions", len(output.deleted_txns))
        self.logger.info("Skipped %s transactions", len(output.unprocessed_txns))

        return output

    def changesets(self, transactions_map: IProcessedTransactionsMap, existing_txns):
        change_sets = compute_changes(
            generated_txns=transactions_map.generated_txns,
            imported_txns=existing_txns,
            deleted_txns=transactions_map.deleted_txns,
            work_dir=self.workdir_path,
        )

        parser = make_parser()

        for target_file, change_set in change_sets.items():
            if not target_file.exists():
                if change_set.remove or change_set.update:
                    raise ValueError("Expect new transactions to add only")
                self.logger.info(
                    "Create new bean file %s with %s transactions",
                    target_file,
                    len(change_set.add),
                )

                bean_content = "\n\n".join(map(txn_to_text, change_set.add))
                self.logger.info("New bean file content:\n%s", bean_content)
                new_tree = parser.parse(bean_content)

            if target_file.exists():
                self.logger.info(
                    "Applying change sets (add=%s, update=%s, remove=%s, dangling=%s) with remove_dangling=%s to %s",
                    len(change_set.add),
                    len(change_set.update),
                    len(change_set.remove),
                    len(change_set.dangling or []),
                    self.remove_dangling,
                    target_file,
                )
                tree = parser.parse(target_file.read_text())
                new_tree = apply_change_set(
                    tree=tree,  # type: ignore
                    change_set=change_set,
                    remove_dangling=self.remove_dangling,
                )

            with target_file.open("wt") as fo:
                formatter = Formatter()
                formatter.format(new_tree, fo)  # type: ignore

        table = Table(
            title="Deleted transactions",
            box=box.SIMPLE,
            header_style=TABLE_HEADER_STYLE,
            expand=True,
        )
        table.add_column("File", style=TABLE_COLUMN_STYLE)
        table.add_column("Id", style=TABLE_COLUMN_STYLE)
        deleted_txn_ids = frozenset(txn.id for txn in transactions_map.deleted_txns)
        for target_file, change_set in change_sets.items():
            for txn in change_set.remove:
                if txn.id not in deleted_txn_ids:
                    continue
                table.add_row(
                    escape(str(target_file)) + f":{txn.lineno}",
                    str(txn.id),
                )
        rich.print(Padding(table, (1, 0, 0, 4)))

        return change_sets

    def run(self):
        if (
            self.workdir_path.resolve().absolute()
            not in self.beanfile_path.absolute().parents
        ):
            self.logger.error(
                "The provided beanfile path %s is not a sub-path of workdir %s",
                self.beanfile_path,
                self.workdir_path,
            )
            raise ValueError("Invalid beanfile path")

        parser = make_parser()

        transactions_map = self.process_transaction()

        self.logger.info(
            "Collecting existing imported transactions from Beancount books ..."
        )
        existing_txns = list(
            extract_existing_transactions(
                parser=parser,
                bean_file=self.beanfile_path,
                root_dir=self.workdir_path,
            )
        )
        change_sets = self.changesets(transactions_map, existing_txns)

        self.logger.info(
            "Found %s existing imported transactions in Beancount books",
            len(existing_txns),
        )

        dangling_action = "Delete" if self.remove_dangling else "Ignored"
        table = Table(
            title=f"Dangling Transactions ({dangling_action})",
            box=box.SIMPLE,
            header_style=TABLE_HEADER_STYLE,
            expand=True,
        )
        table.add_column("File", style=TABLE_COLUMN_STYLE)
        table.add_column("Id", style=TABLE_COLUMN_STYLE)
        for target_file, change_set in change_sets.items():
            if not change_set.dangling:
                continue

            for txn in change_set.dangling:
                table.add_row(
                    escape(str(target_file)) + f":{txn.lineno}",
                    str(txn.id),
                )
        rich.print(Padding(table, (1, 0, 0, 4)))

        table = Table(
            title="Generated transactions",
            box=box.SIMPLE,
            header_style=TABLE_HEADER_STYLE,
            expand=True,
        )
        # TODO: add src info
        table.add_column("File", style=TABLE_COLUMN_STYLE)
        table.add_column("Id", style=TABLE_COLUMN_STYLE)
        table.add_column("Source", style=TABLE_COLUMN_STYLE)
        table.add_column("Date", style=TABLE_COLUMN_STYLE)
        table.add_column("Narration", style=TABLE_COLUMN_STYLE)
        for txn in transactions_map.generated_txns:
            sources = str(":").join(txn.sources or [])
            table.add_row(
                escape(str(txn.file)),
                str(txn.id),
                escape(sources),
                escape(str(txn.date)),
                escape(txn.narration),
            )
        rich.print(Padding(table, (1, 0, 0, 4)))

        table = Table(
            title="Unprocessed transactions",
            box=box.SIMPLE,
            header_style=TABLE_HEADER_STYLE,
            expand=True,
        )
        table.add_column("File", style=TABLE_COLUMN_STYLE)
        table.add_column("Line", style=TABLE_COLUMN_STYLE)
        table.add_column("Id", style=TABLE_COLUMN_STYLE)
        table.add_column("Extractor", style=TABLE_COLUMN_STYLE)
        table.add_column("Date", style=TABLE_COLUMN_STYLE)
        table.add_column("Desc", style=TABLE_COLUMN_STYLE)
        table.add_column("Bank Desc", style=TABLE_COLUMN_STYLE)
        table.add_column("Amount", style=TABLE_COLUMN_STYLE, justify="right")
        table.add_column("Currency", style=TABLE_COLUMN_STYLE)
        for txn in transactions_map.unprocessed_txns:
            table.add_row(
                escape(txn.txn.file or ""),
                str(txn.txn.lineno),
                txn.import_id,
                escape(str(txn.txn.extractor)),
                escape(str(txn.txn.date)) if txn.txn.date is not None else "",
                escape(txn.txn.desc) if txn.txn.desc is not None else "",
                escape(txn.txn.bank_desc) if txn.txn.bank_desc is not None else "",
                escape(str(txn.txn.amount)) if txn.txn.amount is not None else "",
                escape(txn.txn.currency) if txn.txn.currency is not None else "",
            )
        rich.print(Padding(table, (1, 0, 0, 4)))

        self.logger.info("done")
