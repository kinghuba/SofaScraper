import dataclasses
import json
import logging
import os


class LocalDataStorage:
    """
    Handles storage of scraped data either as local JSON files or in a database.
    """

    def __init__(
        self,
        default_file_path: str = "data",
    ):
        """
        Args:
            default_file_path (str): Default file path used when none is passed to save_data.
            default_storage_format (StorageFormat): Default format — JSON or DB.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_file_path = default_file_path

    async def get_existing_match_ids(self, file_path: str | None = None) -> set[int]:
        """
        Scan a directory of per-match JSON files and return the set of match IDs
        that have already been scraped.

        Each file is expected to be named {match_id}.json

        Args:
            file_path: Directory to scan.

        Returns:
            A set of integer match IDs found on disk.  Returns an empty set if
            the directory does not exist yet.
        """
        directory = file_path or self.default_file_path

        if not os.path.isdir(directory):
            self.logger.debug(f"Directory '{directory}' does not exist -- treating as empty.")
            return set()

        existing: set[int] = set()

        for filename in os.listdir(directory):
            if not filename.endswith(".json"):
                continue
            stem = filename[:-5]  # strip .json
            try:
                existing.add(int(stem))
            except ValueError:
                self.logger.debug(f"Skipping '{filename}' (not an int)")

        self.logger.debug(f"Found {len(existing)} existing match(es) in '{directory}'")
        return existing

    async def get_existing_dates(self, file_path: str | None = None) -> set[str]:
        """
        Scan a directory of per-date JSON files and return the set of date strings
        that have already been scraped.

        Each file is expected to be named {YYYY-MM-DD}.json.

        Args:
            file_path: Directory to scan.

        Returns:
            A set of ISO date strings (e.g. {"2024-11-12", "2024-11-13"}).
            Returns an empty set if the directory does not exist yet.
        """
        import re

        DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        directory = file_path or os.path.join(self.default_file_path, "dates")

        if not os.path.isdir(directory):
            self.logger.debug(f"Directory '{directory}' does not exist treating as empty.")
            return set()

        existing: set[str] = set()

        for filename in os.listdir(directory):
            if not filename.endswith(".json"):
                continue
            stem = filename[:-5]
            if DATE_RE.match(stem):
                existing.add(stem)
            else:
                self.logger.debug(f"Skipping '{filename}' (not a date)")

        self.logger.debug(f"Found {len(existing)} existing date(s) in '{directory}'")

        self.logger.debug(f"{existing}")
        return existing

    async def save_data(
        self,
        data: dict | list[dict],
        file_path: str | None = None,
        file_name_key: str | None = None,
    ):
        """
        Save scraped data to JSON or upload to a database.

        Args:
            data (dict | list[dict]): Data to save.
            file_path (str, optional): File path for JSON output.
                                       Ignored when storage_format is DB.
            storage_format (StorageFormat, optional): Override the default format.

        Raises:
            ValueError: If data is not a dict or list of dicts.
        """
        if dataclasses.is_dataclass(data):
            data = dataclasses.asdict(data)
        else:
            data = [dataclasses.asdict(e) if dataclasses.is_dataclass(e) else e for e in data]

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("Data must be a dictionary or a list of dictionaries.")

        base_path = file_path or self.default_file_path

        if file_name_key is None:
            if not base_path.endswith(".json"):
                base_path = f"{base_path}.json"

            self._ensure_directory_exists(base_path)
            self._save_as_json(data, base_path)

        else:
            os.makedirs(base_path, exist_ok=True)

            for item in data:
                if file_name_key not in item:
                    raise ValueError(f"Missing '{file_name_key}' in data item: {item}")

                file_name = f"{item[file_name_key]}.json"
                full_path = os.path.join(base_path, file_name)

                self._save_single_json(item, full_path)

    def _save_single_json(self, data: dict, file_path: str):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, default=str)

            self.logger.debug(f"Saved record to {file_path}")

        except Exception as e:
            self.logger.error(f"Error saving JSON to {file_path}: {e!s}", exc_info=True)
            raise

    def _save_as_json(self, data: list[dict], file_path: str):
        """Save or append records to a single JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, default=str)

            self.logger.debug(f"Saved {len(data)} record(s) to {file_path}")

        except Exception as e:
            self.logger.error(f"Error saving JSON to {file_path}: {e!s}", exc_info=True)
            raise

    def _ensure_directory_exists(self, file_path: str):
        """Create the parent directory of file_path if it does not exist."""
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
