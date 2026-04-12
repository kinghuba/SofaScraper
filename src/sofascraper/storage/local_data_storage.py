import json
import logging
import os
from typing import Callable, Optional

from sofascraper.utils.enums import StorageFormat


class LocalDataStorage:
    """
    Handles storage of scraped data either as local JSON files or in a database.
    """

    def __init__(
        self,
        default_file_path: str = "scraped_data",
        default_storage_format: StorageFormat = StorageFormat.JSON,
    ):
        """
        Args:
            default_file_path (str): Default file path used when none is passed to save_data.
            default_storage_format (StorageFormat): Default format — JSON or DB.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_file_path = default_file_path
        self.default_storage_format = default_storage_format

    def save_data(
        self,
        data: dict | list[dict],
        file_path: str | None = None,
        file_name_key: str | None = None,
        storage_format: StorageFormat | None = None,
        file_name_func: Optional[Callable[[dict], str]] = None,
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
        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise ValueError("Data must be a dictionary or a list of dictionaries.")

        format_to_use = (
            storage_format
            if storage_format is not None
            else self.default_storage_format
        )

        if format_to_use == StorageFormat.JSON:
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
                        raise ValueError(
                            f"Missing '{file_name_key}' in data item: {item}"
                        )

                    file_name = f"{item[file_name_key]}.json"
                    full_path = os.path.join(base_path, file_name)

                    self._save_single_json(item, full_path)

        elif format_to_use == StorageFormat.DB:
            self._upload_to_db(data)

        else:
            raise ValueError(
                f"Unsupported storage format: {format_to_use}. "
                f"Supported formats: {', '.join(f.value for f in StorageFormat)}."
            )

    def _save_single_json(self, data: dict, file_path: str):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, default=str)

            self.logger.info(f"Saved record to {file_path}")

        except Exception as e:
            self.logger.error(f"Error saving JSON to {file_path}: {e!s}", exc_info=True)
            raise

    def _save_as_json(self, data: list[dict], file_path: str):
        """Save or append records to a single JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, default=str)

            self.logger.info(f"Saved {len(data)} record(s) to {file_path}")

        except Exception as e:
            self.logger.error(f"Error saving JSON to {file_path}: {e!s}", exc_info=True)
            raise

    def _upload_to_db(self, data: list[dict]):
        """Upload records to the database. Not yet implemented."""
        # TODO: implement database upload
        raise NotImplementedError("Database upload is not yet implemented.")

    def _ensure_directory_exists(self, file_path: str):
        """Create the parent directory of file_path if it does not exist."""
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
