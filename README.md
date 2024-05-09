# beanhub-import

Beanhub-import is a simple, smart, and easy-to-use library for importing extracted transactions from beanhub-extract.
It generates Beancount transactions based on predefined rules.

## Features

- **No code** - you only need to know a little bit about YAML and Jinja2 template syntax.
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
      account: Expenses:Engineering:ServiceSubscription
    Circleci:
      account: Expenses:Engineering:ServiceSubscription
    Adobe:
      account: Expenses:Engineering:ServiceSubscription
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
If you simply want to import transactions from CSV into their beancount files, please checkout [beanhub-cli](https://github.com/LaunchPlatform/beanhub-cli).


