The configuration file is a YAML file that contains the configuration of the importer. The configuration file is used to define the rules that the importer will use to process the data. The configuration file is divided into several sections, each of which defines a different aspect of the importer's behavior.

---

## ::: beancount_importer_rules.data_types
    options:
      show_bases: false
      heading_level: 2
      show_root_toc_entry: false
      members:
        - ImportDoc
        - ImportList
        - IncludeRule
        - ImportRule
        - ActionAddTxn
        - ActionDelTxn
        - ActionIgnore
        - SimpleTxnMatchRule
        - TransactionTemplate
        - DeleteTransactionTemplate
        - MetadataItemTemplate
        - PostingTemplate
        - AmountTemplate
        - StrPrefixMatch
        - StrSuffixMatch
        - StrExactMatch
        - StrContainsMatch
        - StrOneOfMatch
        - DateAfterMatch
        - DateBeforeMatch
        - DateSameDayMatch
        - DateSameMonthMatch
        - DateSameYearMatch
        - TxnMatchVars
        - InputConfig
        - OutputConfig
