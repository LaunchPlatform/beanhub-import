import base64
import csv
import datetime
import decimal
import random
import sys
from os import urandom

import iso8601
from beancount_black.formatter import parse_date


def make_random_id():
    return (
        base64.urlsafe_b64encode(urandom(24))
        .decode("ascii")
        .replace("-", "")
        .replace("_", "")
    )


def get_id_maps():
    account_ids = {}
    txn_ids = {}
    with open(sys.argv[1], "rt") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            account_id = row["account_id"]
            account_ids.setdefault(account_id, make_random_id())

            txn_id = row["transaction_id"]
            if txn_id:
                txn_ids.setdefault(txn_id, make_random_id())

            pending_txn_id = row["pending_transaction_id"]
            if pending_txn_id:
                txn_ids.setdefault(pending_txn_id, make_random_id())
    return account_ids, txn_ids


def main():
    account_ids, txn_ids = get_id_maps()

    output_rows = []
    hardwired_amounts = {
        "Netflix": decimal.Decimal("15.49"),
        "Comcast": decimal.Decimal("50.00"),
    }
    with (
        open(sys.argv[1], "rt", newline="") as input_file,
        open(sys.argv[2], "wt", newline="") as output_file,
    ):
        reader = csv.DictReader(input_file)
        writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames)
        date_shift = random.randint(3, 10)
        time_shift = random.uniform(60 * 60, 60 * 60 * 3)
        writer.writeheader()

        for row in reader:
            for column, value in row.items():
                date = None
                dt = None
                try:
                    date = parse_date(value)
                except (ValueError, TypeError):
                    pass
                try:
                    dt = iso8601.parse_date(value)
                except ValueError:
                    pass
                if date is not None:
                    date += datetime.timedelta(days=date_shift)
                    row[column] = date
                elif dt is not None:
                    dt += datetime.timedelta(seconds=time_shift, days=date_shift)
                    row[column] = dt
                elif column == "amount":
                    name = row["name"]
                    if name in hardwired_amounts:
                        row[column] = "{:.2f}".format(hardwired_amounts[name])
                    else:
                        for i in range(1000):
                            new_amount = decimal.Decimal(value) + decimal.Decimal(
                                random.uniform(-30, 30)
                            )
                            if new_amount > 0:
                                break
                        if new_amount < 0:
                            raise ValueError()
                        row[column] = "{:.2f}".format(new_amount)
                elif column == "account_id":
                    row[column] = account_ids[value]
                elif column == "transaction_id":
                    if value:
                        row[column] = txn_ids[value]
                elif column == "pending_transaction_id":
                    if value:
                        row[column] = txn_ids[value]
            output_rows.append(row)

        output_rows.sort(key=lambda r: r["date"])
        for row in output_rows:
            writer.writerow(row)
    print("done")


if __name__ == "__main__":
    main()
