# Extra attributes

From time to time, you may want to attach extra attributes to the transactions from input rules to make import matching and transaction insertion easier.
We introduced `extra_attrs` to make this possible.
For example, say you have CSV files from different sources and want to treat them differently from the other files.
In this case, you want to attach an `input_group` attribute so that you can match based on it and do the import process a bit differently.
You can use the `extra_attrs` like this:

```yaml
inputs:
- match: "{{ match_path }}"
  config:
    prepend_postings:
      - account: "{{ input_account }}"
        amount:
          number: "{{ amount }}"
          currency: "{{ currency | default('USD', true) }}"
  extra_attrs:
    # define `input_group` extra attribute to be used for matching or rendering
    input_group: "{{ group | default('default') }}"
  loop:
    - match_path: "mercury/*.csv"
      input_account: Assets:Bank:US:Mercury
    - match_path: "chase/*.csv"
      input_account: Liabilities:CreditCard:US:ChaseFreedom
      group: "credit_card"
    - match_path: "citi/*.csv"
      input_account: Liabilities:CreditCard:US:CitiDoubleCash
      group: "credit_card"
```

In the import rules, the extra attribute `input_group` will be available for matching or rendering.
Thus, you can write import matching like this:

```yaml
imports:
  - match:
      input_group:
        equals: credit_card
  # ...
```

## Rendering of `extra_attrs` Jinja2 templates

We render the values of `extra_attrs` as a Jinja2 template right before we process the import rules.
The original transaction attributes are all available to be used in the template.
This is a very powerful feature that allows you to define the arbitrary transformation of the original transaction attributes, making some complex matching logic possible.
For example, here are some extra attributes you can define:

```yaml
inputs:
- match: "*.csv"
  extra_attrs:
    # set attribute to `True` if the transaction amount is bigger than certain value
    high_amount_purchase: "{{ amount > 1000 }}"
    # maybe in some CSV files we want to treat transaction differently after line 5
    after_lineno_5: "{{ lineno > 5}}"
```

Then, you can match transactions like this:

```yaml
imports:
  - match:
      high_amount_purchase:
        equals: "True"
  # ...
```

Of course, you can also use the extra attributes in the generated transactions like this:

```yaml
imports:
  - match:
      extractor: "plaid"
    actions:
      - type: add_txn
        file: "{{ output_file | default('output.bean') }}"
        txn:
          narration: "{{ desc }}"
          metadata:
            - name: high-amount-purchase
              # use the extra attr value like you would do normally with transaction attributes
              value: "{{ high_amount_purchase }}"
          postings:
            - account: "Expenses:Other"
              amount:
                number: "{{ -amount }}"
                currency: "{{ currency | default('USD', true) }}"
```