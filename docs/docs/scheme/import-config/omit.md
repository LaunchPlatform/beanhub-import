# Import Config

The following keys are available for the import configuration:

- `name`: An optional name for the user to comment on this matching rule. Currently, it has no functional purpose.
- `match`: The rule for matching raw transactions extracted from the input CSV files. As described in the Import Match Rule Definition
- `actions`: Decide what to do with the matched raw transactions, as the Import Action Definition describes.

## Import Match Rule Definition

The raw transactions extracted by the beanhub extractor come with many attributes. Here we list only a few from it:

- `extractor`: Name of the extractor
- `file`: The CSV file path
- `lineno`: The row line number
- `date`: Date of the transaction
- `desc`: Description of the transaction
- `bank_desc`: Exact description of the transaction from the bank
- `amount`: Transaction amount
- `currency`: Currency of the transaction

For the complete list of available raw transaction attributes, please read the [beanhub-extract source code](https://github.com/LaunchPlatform/beanhub-extract/blob/master/beanhub_extract/data_types.py) to learn more.

The `match` object should be a dictionary.
The key is the transaction attribute to match, and the value is the regular expression of the target pattern to match.
All listed attributes need to match so that a transaction will considered matched.
Only simple matching logic is possible with the current approach.
We will extend the matching rule to support more complex matching logic in the future, such as NOT, AND, OR operators.
The following matching modes for the transaction value are available.

## Regular expression

When a simple string value is provided, regular expression matching will be used. Here's an example:

```YAML
imports:
  - match:
      desc: "^DoorDash (.+)"
```

## Exact match

To match an exact value, one can do this:

```YAML
imports:
- match:
    desc:
      equals: "DoorDash"
```

## Prefix match

To match values with a prefix, one can do this:

```YAML
imports:
- match:
    desc:
      prefix: "DoorDash"
```

## Suffix match

To match values with a suffix, one can do this:

```YAML
imports:
- match:
    desc:
      suffix: "DoorDash"
```

## Contains match

To match values containing a string, one can do this:

```YAML
imports:
- match:
    desc:
      contains: "DoorDash"
```

## One of match

To match values belonging to a list of values, one can do this:

```YAML
imports:
- match:
    desc:
      one_of:
        - DoorDash
        - UberEats
        - Postmate
```

# Match with variables

From time to time, you may find yourself writing similar import-matching rules with similar transaction templates.
To avoid repeating yourself, you can also write multiple match conditions with their corresponding variables to be used by the template in the same import statement.
For example, you can simply do the following two import statements:

```yaml
imports:
  - name: PG&E Gas
    match:
      extractor:
        equals: "plaid"
      desc:
        prefix: "PGANDE WEB ONLINE "
    actions:
      - txn:
          payee: "{{ payee }}"
          narration: "Paid American Express Blue Cash Everyday"
          postings:
            - account: "Expenses:Util:Gas:PGE"
              amount:
                number: "{{ -amount }}"
                currency: "{{ currency | default('USD', true) }}"

  - name: Comcast
    match:
      extractor:
        equals: "plaid"
      desc: "Comcast"
    actions:
      - txn:
          payee: "{{ payee }}"
          narration: "Comcast"
          postings:
            - account: "Expenses:Util:Internet:Comcast"
              amount:
                number: "{{ -amount }}"
                currency: "{{ currency | default('USD', true) }}"
```

With match and variables, you can write:

```yaml
imports:
  - name: Household expenses
    common_cond:
      extractor:
        equals: "plaid"
    match:
      - cond:
          desc:
            prefix: "PGANDE WEB ONLINE "
        vars:
          account: "Expenses:Util:Gas:PGE"
          narration: "Paid American Express Blue Cash Everyday"
      - cond:
          desc: "Comcast"
        vars:
          account: "Expenses:Housing:Util:Internet:Comcast"
          narration: "Comcast"
    actions:
      - txn:
          payee: "{{ payee }}"
          narration: "{{ narration }}"
          postings:
            - account: "{{ account } "
              amount:
                number: "{{ -amount }}"
                currency: "{{ currency | default('USD', true) }}"
```

The `common_cond` is the condition to meet for all the matches. Instead of a map, you define the match with the `cond` field and the corresponding variables with the `vars` field.
Please note that the `vars` can also be the Jinja2 template and will rendered before feeding into the transaction template.
If there are any original variables from the transaction with the same name defined in the `vars` field, the variables from the `vars` field always override.

# Omit field in the generated transaction

Sometimes, you may want to omit a particular field in your transactions if the value is unavailable instead of leaving it as a blank string.
For example, the `payee` field sometimes doesn't make sense for some transactions, and the value should not even be present.
With a Jinja2 template, it looks like `{{ payee }}`, but without the `payee` value provided by the transaction, it will end up with an ugly empty string like this:

```beancount
2024-02-26 * "" "Interest payment"
  Assets:Bank:US:WellsFargo:Saving                                          0.06 USD
  Income:US:BankInterest                                                   -0.06 USD
```

To solve the problem, you can use a special variable called `omit`.
The field will be omitted when the rendered value equals the randomly generated `omit` value.
Here's an example:


```yaml
imports:
  - match:
      desc: "..."
    actions:
      - txn:
          payee: "{{ payee | default(omit, true) }}"
          narration: "{{ narration }}"
          # ...
```

As a result, if the `payee` value is not present, the payee field will be absent from the generated transaction like this:

```beancount
2024-02-26 * "Interest payment"
  Assets:Bank:US:WellsFargo:Saving                                          0.06 USD
  Income:US:BankInterest                                                   -0.06 USD
```

# Import Action Definition

Currently, there are three types of action for matched raw transactions:

- `add_txn`: Add a transaction to Beancount files
- `del_txn`: Ensure a transaction is deleted from Beancount files
- `ignore`: Mark the transaction as processed and ignore it

The `type` value determines which type of action to use.
If the `type` value is not provided, `add_txn` will be used by default.
Here are the definitions of the available types.

## Add Transaction Action

The following keys are available for the add transaction action:

- `file`: output beancount file name to write the transaction to
- `txn`: the template of the transaction to insert
 
A transaction template is an object that contains the following keys:

- `id`: the optional `import-id` to overwrite the default one. By default, `{{ file | as_posix_path }}:{{ lineno }}` will be used unless the extractor provides a default value.
- `date`: the optional date value to overwrite the default one. By default, `{{ date }}` will be used.
- `flag`: the optional flag value to overwrite the default one. By default, `*` will be used.
- `narration`: the optional narration value to overwrite the default one. By default `{{ desc | default(bank_desc, true) }}` will be used.
- `payee`: the optional payee value of the transaction.
- `tags`: an optional list of tags for the transaction
- `links`: an optional list of links for the transaction
- `metadata`: an optional list of `name` and `value` objects as the metadata items for the transaction.
- `postings`: a list of templates for postings in the transaction.

The structure of the posting template object looks like this.

- `account`: the account of posting
- `amount`: the optional amount object with `number` and `currency` keys
- `price`: the optional amount object with `number` and `currency` keys
- `cost`: the optional template of cost spec

## Delete Transaction Action

The following keys are available for the delete transaction action:

- `txn`: the template of the transaction to insert
 
A deleting transaction template is an object that contains the following keys:

- `id`: the `import-id` value for ensuring transactions to be deleted. By default, `{{ file | as_posix_path }}:{{ lineno }}` will be used unless the extractor provides a default value.

## Ignore Action

Sometimes, we are not interested in some transactions, but if we don't process them, you will still see them appear in the "unprocessed transactions" section of the report provided by our command line tool. To mark one transaction as processed, you can simply use the `ignore` action like this:

```YAML
- name: Ignore unused entries
  match:
    extractor:
      equals: "mercury"
    desc:
      one_of:
      - Mercury Credit
      - Mercury Checking xx1234
  actions:
    - type: ignore
```
