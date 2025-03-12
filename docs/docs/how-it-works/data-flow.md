# Data Flow

For BeanHub Import to import transactions, you need to know that it's not easy because CSV files or other types of transaction files come in different shapes and formats.
To overcome the problem, we built an open-source library, [beanhub-extract](https://github.com/LaunchPlatform/beanhub-extract).
The job of beanhub-extract is simple. It reads all kinds of CSV and transaction files and then provides a standardized transaction data structure for BeanHub Import to consume.

![How BeanHub Extract works](/img/beanhub-extract-diagram.svg){: .center }

Currently, we only support a handful of financial institutions.
The [Plaid](https://plaid.com) CSV file format is the most important for our customers' use case because it covers all the major financial institutions through BeanHub's [Connect](https://beanhub.io/blog/2024/06/24/introduction-of-beanhub-connect/) or [Direct Connect](https://beanhub.io/blog/2025/01/16/direct-connect-repository/) features.
It allows BeanHub users to automatically pull transaction CSV files from banks in a standard format.
Therefore, we cover all the major banks Plaid supports by supporting the Plaid CSV file format.

Despite BeanHub's Connect and Direct Connect features being only for our paid users, it doesn't necessarily mean we don't support formats other than Plaid.
On the contrary, we hope the BeanHub open-source ecosystem will also strive to be useful for non-BeanHub users.
We will try our best to add support in different formats.
You can let us know what format you would like us to support by [opening a GitHub issue](https://github.com/LaunchPlatform/beanhub-extract/issues/new). You can also open a pull request for the format you want to support.


Here are the currently available fields in the `Transaction` data structure beanhub-extract provides:

 - `extractor` - name of the extractor
 - `file` - the filename of import source
 - `lineno` - the entry line number of the source file
 - `reversed_lineno` - the entry line number of the source file in reverse order. comes handy for CSV files in desc datetime order
 - `transaction_id` - the unique id of the transaction
 - `date` - date of the transaction
 - `post_date` - date when the transaction posted
 - `timestamp` - timestamp of the transaction
 - `timezone` - timezone of the transaction, needs to be one of timezone value supported by pytz
 - `desc` - description of the transaction
 - `bank_desc` - description of the transaction provided by the bank
 - `amount` - transaction amount
 - `currency` - ISO 4217 currency symbol
 - `category` - category of the transaction, like Entertainment, Shopping, etc..
 - `subcategory` - subcategory of the transaction, like Entertainment, Shopping, etc..
 - `pending` - pending status of the transaction
 - `status` - status of the transaction
 - `type` - type of the transaction, such as Sale, Return, Debit, etc
 - `source_account` - Source account of the transaction
 - `dest_account` - destination account of the transaction
 - `note` - note or memo for the transaction
 - `reference` - Reference value
 - `payee` - Payee of the transaction
 - `gl_code` - General Ledger Code
 - `name_on_card` - Name on the credit/debit card
 - `last_four_digits` - Last 4 digits of credit/debit card
 - `extra` - All the columns not handled and put into `Transaction`'s attributes by the extractor goes here

## Import flow

Now, with beanhub-extract, we can easily extract transaction data from different sources as a standard data structure.
Next, it would be the job of beanhub-import to look at those transactions provided by beanhub-extract and see what rules they match, then generate corresponding Beancount transactions for you.
Unlike most Beancount or other plaintext accounting importing tools, beanhub-import not only generates the transactions for you but is also smart enough to look at your existing Beancount transactions and update them for you.
Here's how it works:

![BeanHub import flow diagram](/img/beanhub-import-diagram.svg){: .center }

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
For example, the `import-data/mercury/*.csv` rule will match files such as

- import-data/mercury/2023.csv
- import-data/mercury/2024.csv
- import-data/mercury/2025.csv

If no `extractor` provided, we will detect the extractor automatically.
Now that we know which CSV files to extract transactions from, the next step is to use [beanhub-extract](https://github.com/LaunchPlatform/beanhub-extract) to do so.

#### Step 2. Match transactions

We will go through all the matching rules defined in the `imports` section like this:

```YAML
imports:
- name: Gusto fees
  match:
    extractor:
      equals: "mercury"
    desc: GUSTO
  actions:
    # ...
- name: DoorDash
  match:
    extractor:
      equals: "mercury"
    desc: DoorDash
  actions:
    # ...
```

Each transaction from the input step will flow through all of these match statement and see if it matches.

#### Step 3. Perform actions

If there is a match, corresponding actions, usually adding a transaction, will be performed.
If there's multiple matches, we only perform actions in the first one.

```yaml
imports:
- name: Gusto fees
  match:
    extractor:
      equals: "mercury"
    desc: GUSTO
  actions:
    # This action will be performed
    - txn:
        narration: "Gusto subscription fee"
        postings:
          - account: Expenses:Office:Supplies:SoftwareAsService
            amount:
              number: "{{ -amount }}"
              currency: "{{ currency | default('USD', true) }}"
      # by default, add_txn action type will be used if not provided, so we can omit here
      # type: add_txn
```

The matched CSV transaction attributes will be provided as the values to render the Jinja2 template of the Beancount transaction.
If it's a `add_txn` action, and the input file has `prepend_postings` or `append_postings`, we will combine the postings into the generated transactions.

#### Step 4. Collect existing Beancount transactions

To avoid generating duplicate transactions in the Beancount file, we need to traverse the Beancount folder and find all the existing transactions that were previously imported.

#### Step 5. Compute change sets and apply changes

Now, with the generated transactions from the import rules and the existing Beancount transactions we previously inserted into Beancount files, we can compare and compute the required changes to make it up-to-date.

Finally, with the change sets generated from the previous step, we use our [beancount-parser](https://github.com/LaunchPlatform/beancount-parser) to parse the existing Beancount files as syntax trees, transform them accordingly, and then write them back with our [beancount-black](https://github.com/LaunchPlatform/beancount-black) formatter.

And that's it! Now, all the imported transactions are up-to-date.
