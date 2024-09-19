# Import Doc

The import file should be located at `.beanhub/imports.yaml`. It has the following keys:

- `context`: a dictionary for global variable definitions to be referenced in all Jinja2 template rendering and transaction generation, as described in the [Context Definition](#context-definition) section.
- `inputs`: Define which CSV files to import and their corresponding configurations, as described in the [Input Definition](#input-definition) section
- `imports`: Define rules for which raw transactions to match and what to do with them. As described in the [Import Definition](#import-config-definition) section, new transactions will usually be generated based on the provided templates.
- `outputs`: Define configurations for output files, currently not implemented yet
