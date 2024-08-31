from beancount_importer_rules.engine import ImportRuleEngine
from tests.conftest import FIXTURE_FOLDER


def test_engine_instantiate():
    workdir = FIXTURE_FOLDER / "engine"
    config_path = FIXTURE_FOLDER / "engine" / "import.yaml"
    beanfile_path = FIXTURE_FOLDER / "engine" / "books" / "main.bean"

    engine = ImportRuleEngine(
        workdir=str(workdir),
        config_path=str(config_path),
        beanfile_path=str(beanfile_path),
        remove_dangling=False,
        log_level="info",
    )

    assert engine


def test_engine_run():
    workdir = FIXTURE_FOLDER / "engine"
    config_path = FIXTURE_FOLDER / "engine" / "import.yaml"
    beanfile_path = FIXTURE_FOLDER / "engine" / "books" / "main.bean"

    engine = ImportRuleEngine(
        workdir=str(workdir),
        config_path=str(config_path),
        beanfile_path=str(beanfile_path),
        remove_dangling=False,
        log_level="info",
    )

    engine.run()
    assert engine
