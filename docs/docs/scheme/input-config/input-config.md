# Input Config

Input definition comes with following keys:

- `match`: Rule for matching CSV files. Currently, only the Simple File Match rule is supported. Please see the [Simple File Match](./match.md) section for more details.
- `config`: The configuration of the matched input CSV files. Please see the [Config](./config.md) section.
- `filter`: The conditions for filtering transactions extracted from the input files. Optional. Please see the [Filter](./filter.md) section.
- `loop`: Repeating the same input configuration template with different variables to avoid repeating. Optional. Please see the [Loop](./loop.md) section.
