# Filter

In many situations, you may want to include only particular transactions from the input CSV files.
For example, say you have been hand-crafting your books for 2024.
At the beginning of 2025, you've decided to start using BeanHub Import to generate transactions with pre-defined rules.
You wrote inputs like this:

```yaml
inputs:
  - match: "import-data/mercury/*.csv"
    config:
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: Assets:Bank:US:Mercury
          amount:
            number: "{{ amount }}"
            currency: "{{ currency | default('USD', true) }}"
```

However, the input data from services like BeanHub's [Direct Connect](https://academy.beanhub.io/automation/bank-txns/beanhub-direct-connect/) usually provides bank transaction CSV files that go back a few years.
It may include the transactions from 2024 as well.
Since you already have your transactions in 2024 handwritten, you want to exclude transactions before 2025-01-01.
In that case, you can use a filter to filter out transactions before 2025-01-1.

```yaml
inputs:
  - match: "import-data/mercury/*.csv"
    config:
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: Assets:Bank:US:Mercury
          amount:
            number: "{{ amount }}"
            currency: "{{ currency | default('USD', true) }}"
    filter:
      # this filter will ignore all the transactions before 2025-01-01
      - field: date
        op: ">="
        value: "2025-01-01"
```

In this way, BeanHub Import will ignore transactions even if 2024 or even 2023 CSV files exist in the input folder and match the filename pattern.

## Schema

The optional `filter` field is a list of objects containing the following keys:

- `field`: the field name of the input transactions extracted from the input file. For example, `date`, `extractor`, `lineno` and, etc. Please read the beanhub-extract source code to see what the available fields are.
- `op`: the type of operators. Currently, we support the following:
    - `==`: Equal
    - `!=`: Not Equal
    - `>`: Greater Than
    - `>=`: Greater Than or Equal
    - `<`: Less Than
    - `<=`: Less Than or Equal
- `value`: the target value to apply with the operator.

If the list provides more than one filter operation, it will apply the `AND` logic and include only the transactions with all conditions met.
If you need more complex logic for your use case, please open an issue in our GitHub repository.
