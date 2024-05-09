# beanhub-import [![CircleCI](https://dl.circleci.com/status-badge/img/gh/LaunchPlatform/beanhub-import/tree/master.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/LaunchPlatform/beanhub-import/tree/master)

Beanhub-import is a simple, smart, and easy-to-use library for importing extracted transactions from beanhub-extract.
It generates Beancount transactions based on predefined rules.

**Note**: This project is still in early stage, still subject to rapid major changes

## Features

- **Easy-to-use** - you only need to know a little bit about YAML and Jinja2 template syntax.
- **Simple declarative rules** - A single import file for all imports
- **Idempotent** - As long as the input data and rules are the same, the Beancount files will be the same.
- **Auto-update existing transactions** - When you update the rules or data, corresponding Beancount transactions will be updated automatically. 
- **Auto-move transactions to a different file** - When you change the rules to output the transactions to a different file, it will automatically remove the old ones and add the new ones for you
- **Merge data from multiple files (coming soon)** - You can define rules to match transactions from multiple sources for generating your transactions

## Why?

There are countless Beancount importer projects out there, so why do we have to build a new one from the ground up?
We are building a new one with a completely new design because we cannot find an importer that meets our requirements for [BeanHub](https://beanhub.io).
There are a few critical problems we saw in the existing Beancount importers:

- Need to write Python code to make it work
- Doesn't handle duplication problem
- Hard to reuse because extracting logic is coupled with generating logic
- Hard to customize for our own needs
- Can only handle a single source file

## Example

The rules of beanhub-import is defined in YAML format at `.beanhub/imports.yaml`. Here's an example

```YAML
# the `context` defines global variables to be referenced in the Jinja2 template for
# generating transactions
context:
  routine_expenses:
    "Amazon Web Services":
      account: Expenses:Engineering:Servers:AWS
    Netlify:
      account: Expenses:Engineering:ServiceSubscription
    Mailchimp:
      account: Expenses:Marketing:ServiceSubscription
    Circleci:
      account: Expenses:Engineering:ServiceSubscription
    Adobe:
      account: Expenses:Design:ServiceSubscription
    Digital Ocean:
      account: Expenses:Engineering:ServiceSubscription
    Microsoft:
      account: Expenses:Office:Supplies:SoftwareAsService
      narration: "Microsoft 365 Apps for Business Subscription"
    Mercury IO Cashback:
      account: Expenses:CreditCardCashback
      narration: "Mercury IO Cashback"
    WeWork:
      account: Expenses:Office
      narration: "Virtual mailing address service fee from WeWork"

# the `inputs` defines which files to import, what type of beanhub-extract extractor to use,
# and other configurations, such as `prepend_postings` or default values for generating
# a transaction
inputs:
  - match: "import-data/mercury/*.csv"
    config:
      # use `mercury` extractor for extracting transactions from the input file
      extractor: mercury
      # the default output file to use
      default_file: "books/{{ date.year }}.bean"
      # postings to prepend for all transactions generated from this input file
      prepend_postings:
        - account: Assets:Bank:US:Mercury
          amount:
            number: "{{ amount }}"
            currency: "{{ currency | default('USD', true) }}"

# the `imports` defines the rules to match transactions extracted from the input files and
# how to generate the transaction
imports:
  - name: Routine expenses
    match:
      extractor:
        equals: "mercury"
      desc:
        one_of:
          - Amazon Web Services
          - Netlify
          - Mailchimp
          - Circleci
          - WeWork
          - Adobe
          - Digital Ocean
          - Microsoft
          - Mercury IO Cashback
    actions:
      # generate a transaction into the beancount file
      - file: "books/{{ date.year }}.bean"
        txn:
          narration: "{{ routine_expenses[desc].narration | default(desc, true) | default(bank_desc, true) }}"
          postings:
            - account: "{{ routine_expenses[desc].account }}"
              amount:
                number: "{{ -amount }}"
                currency: "{{ currency | default('USD', true) }}"

  - name: Receive payments from contracting client
    match:
      extractor:
        equals: "mercury"
      desc:
        equals: Evil Corp
    actions:
      - txn:
          narration: "Receive payment from Evil Corp"
          postings:
            - account: "Assets:AccountsReceivable:EvilCorpContracting"
              amount:
                number: "{{ -amount / 300 }}"
                currency: "EVIL.WORK_HOUR"
              price:
                number: "300.0"
                currency: "USD"

  - name: Ignore unused entries
    match:
      extractor:
        equals: "mercury"
      desc:
        one_of:
        - Mercury Credit
        - Mercury Checking xx1234
    actions:
      # ignore action is a special type of import rule action to tell the importer to ignore the
      # transaction so that it won't show up in the "unprocessed" section in the import result
      - type: ignore

```

## Usage

This project is a library and not meant for end-users.
If you simply want to import transactions from CSV into their beancount files, please checkout the `import` command of [beanhub-cli](https://github.com/LaunchPlatform/beanhub-cli).

## Scheme definition

### Import Doc

The import file should be located at `.beanhub/imports.yaml`. It has the following keys:

- `context`: a dictionary for global variable definitions to be referenced in all Jinja2 template rendering and transaction generation, as described in the [Context Definition](#context-definition) section.
- `inputs`: Define which CSV files to import and their corresponding configurations, as described in the [Input Definition](#input-definition) section
- `imports`: Define rules for which raw transactions to match and what to do with them. As described in the [Import Definition](#import-config-definition) section, new transactions will usually be generated based on the provided templates.
- `outputs`: Define configurations for output files, currently not implemented yet

### Context Definition

Context comes in handy when you need to define variables to be referenced in the template. As you can see in the example, we define a `routine_expenses` dictionary variable in the context. 

```YAML
context:
  routine_expenses:
    "Amazon Web Services":
      account: Expenses:Engineering:Servers:AWS
    Netlify:
      account: Expenses:Engineering:ServiceSubscription
    Mailchimp:
      account: Expenses:Marketing:ServiceSubscription
    Circleci:
      account: Expenses:Engineering:ServiceSubscription
    Adobe:
      account: Expenses:Design:ServiceSubscription
    Digital Ocean:
      account: Expenses:Engineering:ServiceSubscription
    Microsoft:
      account: Expenses:Office:Supplies:SoftwareAsService
      narration: "Microsoft 365 Apps for Business Subscription"
    Mercury IO Cashback:
      account: Expenses:CreditCardCashback
      narration: "Mercury IO Cashback"
    WeWork:
      account: Expenses:Office
      narration: "Virtual mailing address service fee from WeWork"
```

Then, in the transaction template, we look up the dictionary to find out what narration value to use:

```
"{{ routine_expenses[desc].narration | default(desc, true) | default(bank_desc, true) }}"
```

### Input Definition

Input definition comes with two keys:

- `match`: Rule for matching CSV files. Currently, only the Simple File Match rule is supported. Please see the [Simple File Match Definition](#simple-file-match-definition) section for more details.
- `config`: The configuration of the matched input CSV files. Please see the [Input Config Definition](#input-config-definition) section.

#### Simple File Match Definition

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

#### Input Config Definition

The following keys are available for the input configuration:

- `extractor`: Which extractor from `beanhub-extract` should be used? Currently, only extractors from `beanhub-extract` are supported, and you always need to specify it explicitly. We will open up to support a third-party extractor, and we will also add an auto-detection feature so that it will guess which extractor to use for you.
- `default_file`: The default output file for generated transactions from the matched file to use if not specified in the `add_txn` action.
- `prepend_postings`: Postings are to be prepended for the generated transactions from the matched file. A list of posting templates as described in the [Add Transaction Action](#add-transaction-action) section.
- `append_postings`: Postings are to be appended to the generated transactions from the matched file. A list of posting templates as described in the [Add Transaction Action](#add-transaction-action) section.
- `default_txn`: The default transaction template values to use in the generated transactions from the matched file. Please see the [Add Transaction Action](#add-transaction-action) section.

### Import Config Definition

The following keys are available for the import configuration:

- `name`: An optional name for the user to comment on this matching rule. Currently, it has no functional purpose.
- `match`: The rule for matching raw transactions extracted from the input CSV files. As described in the Import Match Rule Definition
- `actions`: Decide what to do with the matched raw transactions, as the Import Action Definition describes.

#### Import Match Rule Definition

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

##### Regular expression

When a simple string value is provided, regular expression matching will be used. Here's an example:

```YAML
imports:
  - match:
      desc: "^DoorDash (.+)"
```

##### Exact match

To match an exact value, one can do this:

```YAML
imports:
- match:
    desc:
      equals: "DoorDash"
```

##### Prefix match

To match values with a prefix, one can do this:

```YAML
imports:
- match:
    desc:
      prefix: "DoorDash"
```

##### Suffix match

To match values with a suffix, one can do this:

```YAML
imports:
- match:
    desc:
      suffix: "DoorDash"
```

##### Contains match

To match values containing a string, one can do this:

```YAML
imports:
- match:
    desc:
      contains: "DoorDash"
```

##### One of match

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

#### Import Action Definition

Currently, there are two types of action for matched raw transactions:

- `add_txn`: Add a transaction to Beancount files
- `ignore`: Mark the transaction as processed and ignore it

The `type` value determines which type of action to use.
If the `type` value is not provided, `add_txn` will be used by default.
Here are the definitions of the available types.

##### Add Transaction Action

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


##### Ignore Action

Sometimes, we are not interested in some transactions, but if we don't process them, you will still see them appear in the "unprocessed transactions" section of the report provided by our command line tool. To mark one transaction as processed, you can simply use the `ignore` action like this:

```YAML
- name: Ignore unused entries
  match:
    extractor:
      equals: "mercury"
    desc:
      one_of:
      - Mercury Credit
      - Mercury Checking xx1462
  actions:
    - type: ignore
```

## Sponsor

<p align="center">
  <a href="https://beanhub.io"><img src="https://github.com/LaunchPlatform/beanhub-extract/raw/master/assets/beanhub.svg?raw=true" alt="BeanHub logo" /></a>
</p>

A modern accounting book service based on the most popular open source version control system [Git](https://git-scm.com/) and text-based double entry accounting book software [Beancount](https://beancount.github.io/docs/index.html).

## How it works

### Unique import id for transactions extracted from the CSV files
The biggest challenge we face when designing this system is finding a way to deduplicate the imported transactions from CSV. Obviously, we need a way to tell which transactions were already imported into Beancount files so that we don't need to import them again. To make this happen, we introduce the concept of `import-id`. Each transaction extracted from CSV files should have a unique import ID for us to identify. In this way, we can process the existing Beancount files and find out which transactions have already been imported. We add a metadata item with the key `import-id` to the transaction. Here's an example.

```
2024-04-15 * "Circleci"
  import-id: "<unique import id>"
  Assets:Bank:US:MyBank                              -30.00 USD
  Expenses:Engineering:ServiceSubscription            30.00 USD 
```

The next question will then be: What should be the unique ID for identifying each transaction in the CSV files? If the CSV files come with an ID column that already has a unique value, we can surely use it. However, what if there's no such value in the file? As we observed, most CSV files exported from the bank come with rows ordered by date. The straightforward idea is to use `filename + lineno` as the id. The Jinja2 template would look like this.

```jinja2
{{ file }}:{{ lineno }}
```

Then with a transaction from row 123 in the file `import-data/mybank/2024.csv` should have an import ID like this.

```
import-data/mybank/2024.csv:123
```

As most of the bank transactions export CSV files have transactions come in sorted order by date, even if there are new transactions added and we export the CSV file for the same bank again and overwrite the existing file, there will only be new lines added at the bottom of the file.
Like this:

<p align="center">
  <img src="https://github.com/LaunchPlatform/beanhub-import/raw/master/assets/csv-file-diff.png?raw=true" alt="Diff of CSV file adding only new lines at the end" />
</p>

The line number of older transactions from the same CSV file with the same export time range and filter settings should remain the same. The file name and line number serve as a decent default unique identifier for the transactions from CSV files.

Although this approach works for most CSV files sorted by date in ascending order, it won't work for files in descending order.
For example, CSV files exported from [Mercury](https://mercury.com/) came in descending order.
Obviously, any new transactions added to the export file will change the line number for all previously imported transactions.
To overcome the problem, we also provide `reverse_lineno` attribute in the extracted transaction.
It's the `lineno - total_row_count` value. As you may have noticed, we intentionally made the number negative.
It's trying to make it clear that this line (or row) number is in the reversed order, just like Python's negative index for accessing elements from the end.

With that, we can define the import ID for Mercury CSV files like this:

```jinja2
{{ file }}:{{ reversed_lineno }}
```

Since each CSV file may have its own unique best way to reliably identify a transaction, we add an optional default importer ID value to extractors in the [beanhub-extract](https://github.com/LaunchPlatform/beanhub-extract) library as `DEFAULT_IMPORT_ID`.
Please note that these values are just default ones. Users can still override the default import ID Jinja2 template by setting the `id` value for their `add_txn` action in the import rule.

### The flow of beanhub-import

Now, as you know, we can produce transactions and insert them into Beacount files with unique import IDs so that we can trace them. The next would be putting all the pieces together. Here's the flow diagram of how beanhub-import works:

<p align="center">
  <img src="https://github.com/LaunchPlatform/beanhub-import/raw/master/assets/beanhub-import-flow.svg?raw=true" alt="BeanHub import flow diagram" />
</p>

#### Step 1. Match input CSV files

Input rules are defined as shown in this example:

```YAML
inputs:
  - match: "import-data/mercury/*.csv"
    config:
      extractor: mercury
      default_file: "books/{{ date.year }}.bean"
      prepend_postings:
        - account: Assets:Bank:US:Mercury
          amount:
            number: "{{ amount }}"
            currency: "{{ currency | default('USD', true) }}"
```

First, we must find all the matched CSV files based on the rule.

#### Step 2. Extract transactions from the CSV files

Now that we know which CSV files to extract transactions from, the next step is to use [beanhub-extract](https://github.com/LaunchPlatform/beanhub-extract) to do so.

#### Step 3. Merge & generate transactions

The design of this step is still working in progress, but we envision you can define "merge" rules like this:

```YAML
merges:
- match:
  - name: mercury
    extractor:
      equals: "mercury"
    desc: "Credit card payment"
    merge_key: "{{ date }}:{{ amount }}"
  - name: chase
    extractor:
      equals: "chase"
    desc: "Payment late fee"
    merge_key: "{{ post_date }}:{{ amount }}"
  actions:
    - txn:
        narration: "Paid credit card"
        postings:
          - account: Expenses:CreditCardPayment
            amount:
              number: "{{ -mercury.amount }}"
              currency: "{{ mercury.currency | default('USD', true) }}"
          - account: Expenses:LateFee
            amount:
              number: "{{ -chase.amount }}"
              currency: "{{ chase.currency | default('USD', true) }}"
```

It will match multiple transactions from the CSV input files and generate Beancount transactions accordingly.

#### Step 4. Match & generate transactions

For CSV transactions not matched in the merge step, we will apply all the matching rules defined in the `imports` section like this:

```YAML
imports:
- name: Gusto fees
  match:
    extractor:
      equals: "mercury"
    desc: GUSTO
  actions:
    - txn:
        narration: "Gusto subscription fee"
        postings:
          - account: Expenses:Office:Supplies:SoftwareAsService
            amount:
              number: "{{ -amount }}"
              currency: "{{ currency | default('USD', true) }}"
```

If there is a match, corresponding actions, usually adding a transaction, will be performed.
The matched CSV transaction attributes will be provided as the values to render the Jinja2 template of the Beancount transaction.

#### Step 5. Collect existing Beancount transactions

To avoid generating duplicate transactions in the Beancount file, we need to traverse the Beancount folder and find all the existing transactions that were previously imported.

#### Step 6. Compute change sets

Now, with the generated transactions from the import rules and the existing Beancount transactions we previously inserted into Beancount files, we can compare and compute the required changes to make it up-to-date.

#### Step 7. Apply changes

Finally, with the change sets generated from the previous step, we use our beancount-parser to parse the existing Beancount files as syntax trees, transform them accordingly, and then write them back with our [beancount-black](https://github.com/LaunchPlatform/beancount-black) formatter.

And that's it! Now, all the imported transactions are up-to-date.
