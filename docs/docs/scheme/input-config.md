# Input Config

Input definition comes with two keys:

- `match`: Rule for matching CSV files. Currently, only the Simple File Match rule is supported. Please see the [Simple File Match](#simple-file-match) section for more details.
- `config`: The configuration of the matched input CSV files. Please see the [Input Config](#input-config) section.

# Simple File Match

Currently, we support three different modes of matching a CSV file. The first one is the default one, glob. A simple string would make it use glob mode like this:

```YAML
inputs:
  - match: "import-data/mercury/*.csv"
```

You can also do an exact match like this:

```YAML
inputs:
- match:
    equals: "import-data/mercury/2024.csv"
```

Or, if you prefer regular expression:

```YAML
inputs:
- match:
    regex: "import-data/mercury/2([0-9]+).csv"
```

## Input Config

The following keys are available for the input configuration:

- `extractor`: Which extractor from `beanhub-extract` should be used? Currently, only extractors from `beanhub-extract` are supported, and you always need to specify it explicitly. We will open up to support a third-party extractor, and we will also add an auto-detection feature so that it will guess which extractor to use for you.
- `default_file`: The default output file for generated transactions from the matched file to use if not specified in the `add_txn` action.
- `prepend_postings`: Postings are to be prepended for the generated transactions from the matched file. A list of posting templates as described in the [Add Transaction Action](./import-config/actions.md#add-transaction-action) section.
- `append_postings`: Postings are to be appended to the generated transactions from the matched file. A list of posting templates as described in the [Add Transaction Action](./import-config/actions.md#add-transaction-action) section.
- `default_txn`: The default transaction template values to use in the generated transactions from the matched file. Please see the [Add Transaction Action](./import-config/actions.md#add-transaction-action) section.
