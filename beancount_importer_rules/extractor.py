# an extract is a class that returns a callable
# the callable accepts a file and returns a list of transactions
import csv
import datetime
import hashlib
import os
import sys
import typing
from importlib import import_module
from pathlib import Path

from beancount_importer_rules.data_types import Fingerprint, Transaction

type ExtractorFactory = typing.Callable[[str], type[ExtractorBase]]


class ExtractorError(Exception):
    def __init__(self, module: str, klass_name: str):
        self.module = module
        self.klass_name = klass_name


class ExtractorImportError(ExtractorError):
    def __str__(self):
        return f"Could not import module {self.module}"


class ExtractorClassNotFoundError(ExtractorError):
    def __str__(self):
        return f"Could not find class {self.klass_name} in module {self.module}"


class ExtractorClassNotSubclassError(ExtractorError):
    def __str__(self):
        return f"Class {self.klass_name} in module {self.module} is not a subclass of ExtractorBase"


class ExtractorClassInvalidInputFileError(ExtractorError):
    def __str__(self):
        return f"Class {self.klass_name} in module {self.module} does not accept input_file=None"


class ExtractorClassInvalidInputMissingFileNameError(ExtractorError):
    def __str__(self):
        return (
            f"Class {self.klass_name} in module {self.module} does not have a filename"
        )


class ExtractorClassIncorrectlyCraftedError(ExtractorError):
    def __str__(self):
        return f"Class {self.klass_name} in module {self.module} is incorrectly crafted"


def create_extractor_factory(
    class_name: typing.Optional[str] = None,
    working_dir: Path = Path.cwd(),
) -> ExtractorFactory:
    """
    Manages importing the defined extractor module and returning the extractor
    """

    class_name = class_name or "Importer"
    working_dir = working_dir
    sys.path.append(str(working_dir))

    def get_extractor(extrator_name: str) -> type[ExtractorBase]:
        # set the import path to the working directory
        bits = extrator_name.split(":")
        module_import = bits[0]
        module_class = bits[1] if len(bits) > 1 else class_name

        try:
            module = import_module(module_import)
        except ImportError:
            raise ExtractorImportError(
                module=module_import,
                klass_name=module_class,
            )

        try:
            klass = getattr(module, module_class)
        except AttributeError:
            raise ExtractorClassNotFoundError(
                module=module_import,
                klass_name=module_class,
            )

        if not issubclass(klass, ExtractorBase):
            raise ExtractorClassNotSubclassError(
                module=module_import,
                klass_name=module_class,
            )

        return klass

    return get_extractor


DEFAULT_IMPORT_ID_TEMPLATE: str = "{{ file | as_posix_path }}:{{ reversed_lineno }}"


class ExtractorBase:
    input_file: typing.TextIO
    """The input file to be processed"""

    def __init__(self, input_file: typing.TextIO | None = None):
        if input_file is None:
            raise ExtractorClassInvalidInputFileError(
                module=self.__module__,
                klass_name=self.__class__.__name__,
            )
        self.input_file = input_file

        self.filename = None
        if not hasattr(self.input_file, "name"):
            raise ExtractorClassInvalidInputMissingFileNameError(
                module=self.__module__,
                klass_name=self.__class__.__name__,
            )

        self.filename = self.input_file.name

    def get_import_id_template(self) -> str:
        return DEFAULT_IMPORT_ID_TEMPLATE

    def detect(self) -> bool:
        raise NotImplementedError()

    def fingerprint(self) -> Fingerprint | None:
        raise NotImplementedError()

    def parse_date(self, date_str: str) -> datetime.date:
        raise NotImplementedError()

    def process(self) -> typing.Generator[Transaction, None, None]:
        raise NotImplementedError()


class ExtractorCsvBase(ExtractorBase):
    """
    Base class for CSV extractors
    """

    date_format: str = "%d/%m/%Y"
    """The date format the CSV file uses"""

    datetime_format: str = "%d/%m/%Y %H:%M:%S"
    """The datetime format the CSV file uses"""

    date_field: str = "Date"
    """The date field in the CSV file"""

    fields: typing.List[str]
    """The fields in the CSV file"""

    linecount: int = 0
    """The number of lines in the CSV file. Computed on initialization"""

    def __init__(self, input_file: typing.TextIO | None = None):
        super().__init__(input_file)

        line_count_reader = csv.DictReader(self.input_file)
        line_count = 0

        for _ in line_count_reader:
            line_count += 1

        self.line_count = line_count

    def parse_date(self, date_str: str) -> datetime.date:
        """
        Parse a date string using the self.date_format
        """
        return datetime.datetime.strptime(date_str, self.date_format).date()

    def parse_time(self, date_str: str) -> datetime.datetime:
        """
        Parse a date string using the self.date_format
        """
        return datetime.datetime.strptime(date_str, self.datetime_format)

    def fingerprint(self) -> Fingerprint | None:
        """
        Generate a fingerprint for the CSV file
        """
        if self.input_file is None:
            raise ValueError("input_file is None")

        reader = csv.DictReader(self.input_file)
        if reader.fieldnames is None:
            return

        row = None
        for row in reader:
            pass

        if row is None:
            return

        hash = hashlib.sha256()
        for field in reader.fieldnames:
            hash.update(row[field].encode("utf8"))

        return Fingerprint(
            starting_date=self.parse_date(row[self.date_field]),
            first_row_hash=hash.hexdigest(),
        )

    def detect(self) -> bool:
        """
        Check if the input file is a CSV file with the expected
        fields. Should this extractor be used to process the file?
        """
        if not hasattr(self.input_file, "name"):
            return False

        if self.fields is None:
            raise ExtractorClassIncorrectlyCraftedError(
                module=self.__module__,
                klass_name=self.__class__.__name__,
            )

        if self.input_file is None:
            raise ExtractorClassInvalidInputFileError(
                module=self.__module__, klass_name=self.__class__.__name__
            )

        reader = csv.DictReader(self.input_file)
        try:
            return reader.fieldnames == self.fields
        except Exception:
            return False

    def detect_has_header(self) -> bool:
        """
        Check if the supplied csv file has a header row.

        It will if the fieldnames attribute is not None and they match the
        values of the first row of the file.
        """
        if not hasattr(self.input_file, "name"):
            return False

        if self.fields is None:
            raise ExtractorClassIncorrectlyCraftedError(
                module=self.__module__,
                klass_name=self.__class__.__name__,
            )

        if self.input_file is None:
            raise ExtractorClassInvalidInputFileError(
                module=self.__module__, klass_name=self.__class__.__name__
            )

        reader = csv.DictReader(self.input_file)
        try:
            return reader.fieldnames == self.fields
        except Exception:
            return False

    def process_line(self, lineno: int, line: dict) -> Transaction:
        raise NotImplementedError()

    def process(self) -> typing.Generator[Transaction, None, None]:
        self.input_file.seek(os.SEEK_SET, 0)
        start_row = self.detect_has_header() and 1 or 0
        reader = csv.DictReader(self.input_file, fieldnames=self.fields)

        for lineno, line in enumerate(reader, start=start_row):
            yield self.process_line(lineno, line)
