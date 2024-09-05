# Getting Started

### 1. Install the package

[pip](https://pypi.org/project/pip/)
```bash
pip install mypackage
```

[poetry](https://python-poetry.org/)
```bash
poetry add mypackage
```

[pdm](https://pdm.fming.dev/)
```bash
pdm add mypackage
```

### 2. Create extractors

::: beancount_importer_rules.extractor.ExtractorCsvBase.__getting_started__
    options:
      show_root_toc_entry: false
      show_bases: false
      show_source: false

### 3. Create import rules

::: beancount_importer_rules.data_types.ImportDoc
    options:
      show_root_toc_entry: false
      show_bases: false
      show_source: false

### 4. Run the importer

::: beancount_importer_rules.cli.import_cmd
    options:
      show_root_toc_entry: false
      show_bases: false
      show_source: false


## Read More

- [Configuration](configuration.md)
- [API Reference](api.md)
