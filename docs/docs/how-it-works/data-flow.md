# Data Flow

Now, as you know, we can produce transactions and insert them into Beacount files with unique import IDs so that we can trace them. The next would be putting all the pieces together. Here's the flow diagram of how beanhub-import works:

![BeanHub import flow diagram](/img/beanhub-import-flow.svg){: .center }

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

Finally, with the change sets generated from the previous step, we use our [beancount-parser](https://github.com/LaunchPlatform/beancount-parser) to parse the existing Beancount files as syntax trees, transform them accordingly, and then write them back with our [beancount-black](https://github.com/LaunchPlatform/beancount-black) formatter.

And that's it! Now, all the imported transactions are up-to-date.
