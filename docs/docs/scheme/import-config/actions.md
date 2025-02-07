# Actions

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

- `id`: the optional `import-id` to overwrite the default one. By default, `#!jinja {{ file | as_posix_path }}:{{ lineno }}` will be used unless the extractor provides a default value.
- `date`: the optional date value to overwrite the default one. By default, `#!jinja {{ date }}` will be used.
- `flag`: the optional flag value to overwrite the default one. By default, `*` will be used.
- `narration`: the optional narration value to overwrite the default one. By default `#!jinja {{ desc | default(bank_desc, true) }}` will be used.
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

- `txn`: the template of the transaction to delete (optional)
 
A deleting transaction template is an object that contains the following keys:

- `id`: the `import-id` value for ensuring transactions to be deleted. By default, `#!jinja {{ file | as_posix_path }}:{{ lineno }}` will be used unless the extractor provides a default value.

For example:

```YAML
- name: Delete incorrectly inserted transactions
  match:
    extractor:
      equals: "mercury"
    desc:
      one_of:
      - Mercury Credit
      - Mercury Checking xx1234
  actions:
    - type: del_txn
```

You also can define custom import-ids to be deleted like this:

```YAML
- name: Delete incorrectly inserted transactions
  match:
    extractor:
      equals: "mercury"
    desc:
      one_of:
      - Mercury Credit
      - Mercury Checking xx1234
  actions:
    - type: del_txn
      txn:
        id: "id-{{ file }}:{{ lineno }}"
```

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
