# Simple File Match

Currently, we support three different modes of matching a CSV file. The first one is the default one, glob. A simple string would make it use glob mode like this:

```YAML
inputs:
  - match: "import-data/mercury/*.csv"
```

You can also do an exact match like this:

```YAML
inputs:
- match:
    equals: "import-data/mercury/2024.csv"
```

Or, if you prefer regular expression:

```YAML
inputs:
- match:
    regex: "import-data/mercury/2([0-9]+).csv"
```
