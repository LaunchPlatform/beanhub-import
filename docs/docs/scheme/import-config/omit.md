# Omit Field

Sometimes, you may want to omit a particular field in your transactions if the value is unavailable instead of leaving it as a blank string.
For example, the `payee` field sometimes doesn't make sense for some transactions, and the value should not even be present.
With a Jinja2 template, it looks like `#!jinja {{ payee }}`, but without the `payee` value provided by the transaction, it will end up with an ugly empty string like this:

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
