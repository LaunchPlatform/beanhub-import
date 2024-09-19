# Override Flags

In many cases, you may wish to manually change a transaction without changing the import rules.
You can simply modify the transactions in your Beancount file.
However, with the same `import-id` value, your modifications to the transaction will be overridden the next time you run the beanhub-import command.

For example, say you have a transaction like this.

```
2024-04-15 * "Circleci"
  import-id: "bAPgjNEZj6FaEdqGQP4lsx33gAbQw9umpQAmk"
  Assets:Bank:US:MyBank                                10.00 USD
  Expenses:Engineering:ServiceSubscription            -10.00 USD 
```

Say there's something special about this transaction.
It's a refund instead of a charge due to a billing error.
To make it clear, you can change the narration to "CircleCI refund due to billing error" instead like this

```
2024-04-15 * "CircleCI refund due to billing error"
  import-id: "bAPgjNEZj6FaEdqGQP4lsx33gAbQw9umpQAmk"
  Assets:Bank:US:MyBank                                10.00 USD
  Expenses:Engineering:ServiceSubscription            -10.00 USD 
```

But then, you run

```bash
bh import
```

It will override the changes.
To solve the problem, we provide a metadata item, `import-override`, to control the overriding behavior from transactions generated from the rule to the existing transactions.

There are two modes you can use:

- `none`: Do not override anything. Keep transaction as is
- `all`: Override the existing transaction using the one generated from the automatic import rules.

Other than `none` or `all`, if you want to have fine-grained control over which part of the transactions get overridden, here are available values

- `date`: Date of transaction, e.g. 2024-09-01
- `flag`: Flag of the transaction, e.g., "*" or "!"
- `narration`: Narration of the transaction, e.g., "Purchase lunch."
- `payee`: Payee of the transaction, e.g., "AT&T"
- `hashtags`: Hashtags of the transactions, e.g., "#Rent"
- `links`: Links of the transactions, e.g., "^Travel-to-eu-2023"
- `postings`: Postings of the transactions, e.g., "Assets:Cash -10 USD"

You can combine any of those above with a comma. For example, to allow date and flag overriding, you can set the override mode like this:

```
import-override: "date,flag"
```

For example, say for the transaction you just updated manually, you only want beanhub-import to override the amount, date, postings, and flag, then you can add `import-override` to the transaction like this:

```
2024-04-15 * "CircleCI refund due to billing error"
  import-id: "bAPgjNEZj6FaEdqGQP4lsx33gAbQw9umpQAmk"
  import-override: "date,amount,postings,flag"
  Assets:Bank:US:MyBank                              10.00 USD
  Expenses:Engineering:ServiceSubscription          -10.00 USD 
```

That way, the narration stays the same, but if the source import file changes, the transaction will still be updated accordingly.
