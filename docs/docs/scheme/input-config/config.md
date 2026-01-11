# Config

The following keys are available for the input configuration:

- `extractor`: Which extractor to use for processing the matched file. This can be:

    - A built-in extractor name from `beanhub-extract` (e.g., `mercury`, `chase_credit_card`, `plaid`)
    - A custom extractor via module URI: `module://package.module.ExtractorClass` (e.g., `module://my_extractors.CustomExtractor`)
    - `null` or omitted to enable auto-detection (beanhub-import will try to guess which built-in extractor to use)

    **Note:** Custom extractors loaded via `module://` must:

    - Implement the Extractor interface from beanhub-extract (have `__init__` accepting a file object and `__call__` returning a generator of Transaction objects)
    - Be available in Python's `sys.path` (install the package or set `PYTHONPATH`)
    - Be specified explicitly (auto-detection only works with built-in extractors)

    **Example:**
    ```yaml
    extractor: "module://my_company.extractors.BankOfAmericaExtractor"
    ```

- `default_file`: The default output file for generated transactions from the matched file to use if not specified in the `add_txn` action.
- `prepend_postings`: Postings are to be prepended for the generated transactions from the matched file. A list of posting templates as described in the [Add Transaction Action](../import-config/actions.md#add-transaction-action) section.
- `append_postings`: Postings are to be appended to the generated transactions from the matched file. A list of posting templates as described in the [Add Transaction Action](../import-config/actions.md#add-transaction-action) section.
- `default_txn`: The default transaction template values to use in the generated transactions from the matched file. Please see the [Add Transaction Action](../import-config/actions.md#add-transaction-action) section.
