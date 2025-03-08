# Loop

When you have input files from more than one bank account, usually you will end up writing many repeating input rules like this:

```yaml
inputs:
  - match: "import-data/mercury/*.csv"
    config:
      extractor: mercury
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: Assets:NonBank:US:Mercury
          amount:
            number: "{{ amount }}"
            currency: "{{ currency | default('USD', true) }}"
  - match: "import-data/connect/American Express/Blue Cash Everyday/*.csv"
    config:
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: Liabilities:CreditCard:US:AMEXBlueCashEveryday
          amount:
            number: "{{ -amount }}"
            currency: "{{ currency | default('USD', true) }}"
```

To avoid repetition, we introduced the new optional `loop` field since 1.1.0, which allows you to define multiple inputs with mostly the same configurations by applying the provided variables.
Here's an example of how you can rewrite the above input rules with `loop`.

```yaml
inputs:
  # the `match_path` will be replaced with value provided by the loop variable
  - match: "import-data/{{ match_path }}"
    config:
      extractor: "{{ input_extractor | default(omit) }}"
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        # the `input_account` will be replaced with value provided by the loop variable
        - account: "{{ input_account }}"
          amount:
            # we multiply the amount with amount_scalar to change the sign
            # of amount based on different input files
            number: "{{ amount * amount_scalar }}"
            currency: "{{ currency | default('USD', true) }}"
    loop:
    - match_path: "mercury/*.csv"
      input_account: Assets:NonBank:US:Mercury
      input_extractor: mercury
      amount_scalar: 1
    - match_path: "connect/American Express/Blue Cash Everyday/*.csv"
      input_account: Liabilities:CreditCard:US:AMEXBlueCashEveryday
      amount_scalar: -1
```

## Schema

The optional `loop` field is a simple list of objects containing the key and values to generate each input rule.
The key is the variable name, and the value is the actual value to be rendered in the [Jinja2 templates](https://jinja.palletsprojects.com/en/stable/) in the input rules.

## Loop with filters

A [filter](./filter.md) usually comes as a list, but it can also be a Jinja2 template to be replaced with a variable defined in the loop.
In that way, you can define different filters for each input rule.
For example:

```yaml
inputs:
  - match: "import-data/connect/{{ match_path }}"
    config:
      extractor: "{{ input_extractor | default(omit) }}"
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: "{{ input_account }}"
          amount:
            number: "{{ -amount }}"
            currency: "{{ currency | default('USD', true) }}"
    # the actual filer value will be provided by the loop variable if it's present,
    # otherwise we will omit the filter 
    filter: "{{ input_filter | default(omit) }}"
    loop:
    - match_path: "mercury/*.csv"
      input_account: Assets:NonBank:US:Mercury
      input_filter: 
      - field: date
        op: ">="
        value: "2025-01-01"
    - match_path: "American Express/Blue Cash Everyday/*.csv"
      input_account: Liabilities:CreditCard:US:AMEXBlueCashEveryday
```

If you provide the filter as a list of objects, we will render the content with loop variables as well.
For example:

```yaml
inputs:
  - match: "import-data/connect/{{ match_path }}"
    config:
      extractor: "{{ input_extractor | default(omit) }}"
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: "{{ input_account }}"
          amount:
            number: "{{ -amount }}"
            currency: "{{ currency | default('USD', true) }}"
    filter:
      - field: date
        op: ">="
        # this will be replaced with the actual `begin_date` defined by the loop variables
        value: "{{ begin_date }}"
    loop:
    - match_path: "mercury/*.csv"
      input_account: Assets:NonBank:US:Mercury
      begin_date: "2025-01-01"
    - match_path: "American Express/Blue Cash Everyday/*.csv"
      input_account: Liabilities:CreditCard:US:AMEXBlueCashEveryday
      begin_date: "2024-01-01"
```
