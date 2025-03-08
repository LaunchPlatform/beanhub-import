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

To avoid repetition, we introduced the new optional `loop` field, which allows you to define multiple inputs with mostly the same configurations by applying the provided variables.
Here's an example of how you can rewrite the above input rules with `loop`.

```yaml
inputs:
  - match: "import-data/{{ match_path }}"
    config:
      extractor: "{{ input_extractor | default(omit) }}"
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: "{{ src_account }}"
          amount:
            number: "{{ amount * (amount_scalar | int) }}"
            currency: "{{ currency | default('USD', true) }}"
    loop:
    - match_path: "mercury/*.csv"
      input_account: Assets:NonBank:US:Mercury
      input_extractor: mercury
      amount_scalar: "1"
    - match_path: "connect/American Express/Blue Cash Everyday/*.csv"
      input_account: Liabilities:CreditCard:US:AMEXBlueCashEveryday
      amount_scalar: "-1"
```
