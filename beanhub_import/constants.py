IMPORT_ID_KEY = "import-id"
IMPORT_SRC_KEY = "import-src"
DEFAULT_TXN_TEMPLATE = dict(
    id="{{ file | as_posix_path }}:{{ lineno }}",
    date="{{ date }}",
    flag="*",
    narration="{{ desc | default(bank_desc, true) }}",
)
ADD_ENTRY_LINENO_OFFSET = 100000
