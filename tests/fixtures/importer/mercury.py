import decimal
from typing import Dict, List

import pytz

from beancount_importer_rules.data_types import Transaction
from beancount_importer_rules.extractor import ExtractorCsvBase


class MercuryCsvExtractor(ExtractorCsvBase):
    date_format: str = "%m-%d-%Y"  # month-day-year hour:minute:second
    datetime_format: str = "%m-%d-%Y %H:%M:%S"  # month-day-year hour:minute:second
    date_field: str = "Date (UTC)"
    name: str = "mercury"
    fields: List[str] = [
        "Date (UTC)",
        "Description",
        "Amount",
        "Status",
        "Source Account",
        "Bank Description",
        "Reference",
        "Note",
        "Last Four Digits",
        "Name On Card",
        "Category",
        "GL Code",
        "Timestamp",
        "Original Currency",
    ]

    def process_line(self, lineno: int, line: Dict[str, str]) -> Transaction:
        date = self.parse_date(line.pop("Date (UTC)"))
        desc = line.pop("Description")
        amount = decimal.Decimal(line.pop("Amount"))
        status = line.pop("Status")
        source_account = line.pop("Source Account")
        bank_desc = line.pop("Bank Description")
        reference = line.pop("Reference")
        note = line.pop("Note")
        category = line.pop("Category")
        currency = line.pop("Original Currency")
        name_on_card = line.pop("Name On Card")
        last_four_digits = line.pop("Last Four Digits")
        gl_code = line.pop("GL Code")
        timestamp = pytz.UTC.localize(self.parse_time(line.pop("Timestamp")))

        return Transaction(
            extractor=self.name,
            file=self.filename,
            lineno=lineno + 1,
            reversed_lineno=lineno - self.line_count,
            timezone="UTC",
            extra=line,
            # The following fields are unique to this extractor
            date=date,
            desc=desc,
            amount=amount,
            status=status,
            source_account=source_account,
            bank_desc=bank_desc,
            reference=reference,
            note=note,
            category=category,
            currency=currency,
            name_on_card=name_on_card,
            last_four_digits=last_four_digits,
            gl_code=gl_code,
            timestamp=timestamp,
        )
