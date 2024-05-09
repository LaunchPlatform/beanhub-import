# beanhub-import

Beanhub-extract provides a simple and easy-to-use library for importing extracted transactions.
It generates Beancount transactions based on predefined rules.

## Features

- **No code** - you only need to know a little bit about YAML and Jinja2 template syntax.
- **Simple declarative rules** - A single import file for all imports
- **Idempotent** - As long as the input data and rules are the same, the Beancount files will be the same.
- **Auto-update** existing transactions - When you update the rules or data, corresponding Beancount transactions will be updated automatically. 
- **Auto-move transactions to a different file** - When you change the rules to output the transactions to a different file, it will automatically remove the old ones and add the new ones for you
- **Merge data from multiple files (coming soon)** - You can define rules to match transactions from multiple sources for generating your transactions

## Why?

There are countless Beancount importer projects out there, so why do we have to build a new one from the ground up? We are building a new one with a completely new design because we cannot find an importer that meets our requirements for BeanHub. There are a few critical problems we saw in the existing Beancount importers:

- Need to write Python code to make it work
- Doesn't handle duplication problem
- Hard to reuse because extracting logic is coupled with generating logic
- Hard to customize for our own needs
- Can only handle a single source file

