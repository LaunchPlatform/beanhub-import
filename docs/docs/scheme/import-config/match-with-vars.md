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
