# Import Config

The following keys are available for the import configuration:

- `name`: An optional name for the user to comment on this matching rule. Currently, it has no functional purpose.
- `match`: The rule for matching raw transactions extracted from the input CSV files. As described in the [Import Match Rules](./basic-match.md). Or you can also use [Match with Variables](./match-with-vars.md) instead.
- `actions`: Decide what to do with the matched raw transactions, as the [Import Action](./actions.md) describes.
