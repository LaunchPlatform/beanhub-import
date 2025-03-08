# Import Doc

The import file should be located at `.beanhub/imports.yaml`. It has the following keys:

- `context`: a dictionary for global variable definitions to be referenced in all Jinja2 template rendering and transaction generation, as described in the [Context](./context.md).
- `inputs`: Define which CSV files to import and their corresponding configurations, as described in the [Input Config](input-config/input-config.md).
- `imports`: Define rules for which raw transactions to match and what to do with them. As described in the [Import Config](./import-config/import-config.md) section, new transactions will usually be generated based on the provided templates.
- `outputs`: Define configurations for output files, currently not implemented yet
