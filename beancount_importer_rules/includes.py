import pathlib

import yaml
from pydantic import TypeAdapter

from beancount_importer_rules.data_types import (
    ImportRule,
    IncludeRule,
)

RuleListAdapter = TypeAdapter(list[ImportRule | IncludeRule])


def load_includes(
    workdir_path: pathlib.Path, include_path: pathlib.Path
) -> list[ImportRule]:
    with include_path.open("rt") as fo:
        rules = yaml.safe_load(fo)
        imported = RuleListAdapter.validate_python(rules)
        return resolve_includes(workdir_path=workdir_path, rules=imported)


def resolve_includes(
    workdir_path: pathlib.Path, rules: list[ImportRule | IncludeRule]
) -> list[ImportRule]:
    imports: list[ImportRule] = []

    for rule in rules:
        if isinstance(rule, ImportRule):
            imports.append(rule)
        else:
            # convert to a list of strings
            paths = rule.include if isinstance(rule.include, list) else [rule.include]
            for include_path in paths:
                include_path = workdir_path / include_path
                includes = load_includes(workdir_path, include_path)
                imports.extend(includes)

    return imports
