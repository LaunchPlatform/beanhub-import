# Basic Batch Rules

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

Since it's a very common case where you may want to match a transaction attribute with regular expression but also capture the value from the regular expression groups and use them in your transactions, we added a named group capturing feature since 1.2.0.
For example, to match a description starting with "DoorDash:" and then the restaurant name, you can write a regular expression match like this:

```YAML
imports:
  - match:
      desc: "^DoorDash: (?P<restaurant_name>.+)"
```

With that, you can then use the captured variable `restaurant_name` in generating transactions like this:

```YAML
imports:
  - match:
      desc: "^DoorDash: (?P<restaurant_name>.+)"
    actions:
      - type: add_txn
        txn:
          narration: "Order food via DoorDash from {{ restaurant_name }}"
          # ...
```

For more information about the regular expression named group, please refer to Python's [document for the regular expression module](https://docs.python.org/3/library/re.html).

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

You may often want to match a list of regular expressions instead of exact values.
You can set `regex` as `true` to make it so for that.
You can also add `ignore_case` to `true` to match the in case insensitive mode.
Here's an example:

```YAML
imports:
- match:
    desc:
      regex: true
      ignore_case: true
      one_of:
        - doordash(.+)
        - ubereats(.+)
        - postmate(.+)
```

Capturing name groups as variables for regular expression also works in this case.
For example:

```YAML
imports:
- match:
    desc:
      regex: true
      ignore_case: true
      one_of:
        - doordash(?P<restaurant_name>.+)
        - ubereats(?P<restaurant_name>.+)
        - postmate(?P<restaurant_name>.+)
```

Then, you can use the `restaurant_name` variable like usual.
Since we encounter the first matched regular expression and stop looking further, if there are multiple matches, only the variables from the first one will be captured.
