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
