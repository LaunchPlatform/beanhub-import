import decimal
from typing import Dict, List

from beancount_importer_rules.data_types import Transaction
from beancount_importer_rules.extractor import ExtractorCsvBase


class AgrimasterCsvExtractor(ExtractorCsvBase):
    date_format: str = "%d/%m/%Y"
    date_field: str = "Date"
    name: str = "agrimaster_csv"
    fields: List[str] = [
        "Account",
        "Date",
        "ignore",
        "Description",
        "Amount",
        "Balance",
    ]

    def process_line(self, lineno: int, line: Dict[str, str]) -> Transaction:
        date = self.parse_date(line.pop("Date"))
        description = line.pop("Description")
        amount = decimal.Decimal(line.pop("Amount"))

        return Transaction(
            extractor=self.name,
            file=self.filename,
            lineno=lineno + 1,
            reversed_lineno=lineno - self.line_count,
            extra=line,
            # The following fields are unique to this extractor
            date=date,
            amount=amount,
            desc=description,
        )
