# Context Definition

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

```jinja
"{{ routine_expenses[desc].narration | default(desc, true) | default(bank_desc, true) }}"
```
