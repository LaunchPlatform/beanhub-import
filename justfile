export PATH := ".venv/bin:" + env_var('PATH')

default:
    @just --list

setup:
    @echo ""
    @echo "🍜 Setting up project"
    @echo ""

    pdm install

    @echo ""
    @echo "👍 Done"
    @echo ""

types:
    echo "Checking types..."

    pdm run pyright ./beancount_importer_rules

    @echo ""
    @echo "👍 Done"
    @echo ""


lint:
    echo "Linting files..."

    pdm run ruff check

    @echo ""
    @echo "👍 Done"
    @echo ""

test:
    echo "Testing files..."

    pdm run pytest --verbosity=0

    @echo ""
    @echo "👍 Done"
    @echo ""

citest REPORT_OUTPUT="/dev/tty":
    echo "Running tests..."

    pdm run pytest -v \
        --md-report \
        --md-report-flavor gfm \
        --md-report-exclude-outcomes passed skipped xpassed \
        --md-report-output "{{REPORT_OUTPUT}}"

    @echo ""
    @echo "👍 Done"
    @echo ""

unittest:
    echo "Running unit tests..."

    pdm run pytest

    @echo ""
    @echo "👍 Done"
    @echo ""

integrationtest:
    echo "Running integration tests..."

    pdm run beancount-import import \
        -w tests/fixtures/integration \
        -b simple.bean \
        -c import.yaml

    @echo ""
    @echo "👍 Done"
    @echo ""

build:
    echo "Building project..."

    pdm build

    @echo ""
    @echo "👍 Done"
    @echo ""

secrets:
    echo "Checking for secrets..."

    pdm run detect-secrets scan \
        --baseline \
        --exclude-files ".secrets.baseline" \
        --exclude-files ".venv/.*" > .secrets.baseline

    @echo ""
    @echo "👍 Done"
    @echo ""

docs:
    echo "Generating documentation..."

    @echo ""
    @echo "👍 Done"
    @echo ""

docs-serve:
    echo "Serving documentation..."


    @echo ""
    @echo "👍 Done"
    @echo ""

publish ENV="pypi":
    echo "Publishing package..."

    gopass env websites/{{ENV}}/pdm \
        pdm publish --repository {{ENV}}

    @echo ""
    @echo "👍 Done"
    @echo ""
