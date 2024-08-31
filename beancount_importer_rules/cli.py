import json
import os
import pathlib

import click

from beancount_importer_rules.data_types import (
    ImportDoc,
    ImportList,
)
from beancount_importer_rules.engine import ImportRuleEngine
from beancount_importer_rules.environment import (
    LOG_LEVEL_MAP,
)


@click.group()
def cli():
    pass


@cli.command(name="import")
@click.option(
    "-w",
    "--workdir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=str(pathlib.Path.cwd()),
    help="The beanhub project path to work on",
)
@click.option(
    "-b",
    "--beanfile",
    type=click.Path(),
    default="main.bean",
    help="The path to main entry beancount file",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(),
    default=".beancount_imports.yaml",
    help="The path to import config file",
)
@click.option(
    "--remove-dangling",
    is_flag=True,
    help="Remove dangling transactions (existing imported transactions in Beancount files without corresponding generated transactions)",
)
@click.option(
    "-l",
    "--log-level",
    type=click.Choice(
        list(map(lambda key: key.value, LOG_LEVEL_MAP.keys())), case_sensitive=False
    ),
    default=lambda: os.environ.get("LOG_LEVEL", "INFO"),
)
def import_cmd(
    config: str,
    workdir: str,
    beanfile: str,
    remove_dangling: bool,
    log_level: str,
):
    engine = ImportRuleEngine(
        workdir=workdir,
        config_path=config,
        beanfile_path=beanfile,
        remove_dangling=remove_dangling,
        log_level=log_level,
    )

    engine.run()


@cli.command(name="schema")
def schema_cmd():
    output_file_name = "schema.json"
    listoutput_file_name = "schema-import.json"
    with open(output_file_name, "w") as f:
        main_model_schema = ImportDoc.model_json_schema()
        f.write(json.dumps(main_model_schema, indent=2))

    with open(listoutput_file_name, "w") as f:
        list_model_schema = ImportList.model_json_schema()
        f.write(json.dumps(list_model_schema, indent=2))


if __name__ == "__main__":
    cli()
