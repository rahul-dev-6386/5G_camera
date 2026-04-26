import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import get_settings
from .logger import get_logger


settings = get_settings()
storage_dir = Path(settings.storage_dir)
storage_dir.mkdir(parents=True, exist_ok=True)
logger = get_logger(__name__)


@dataclass
class InsertOneResult:
    inserted_id: str | None


class LocalCursor:
    def __init__(self, items: list[dict]):
        self.items = items

    def sort(self, field: str, direction: int) -> "LocalCursor":
        reverse = direction < 0
        self.items.sort(key=lambda item: item.get(field, ""), reverse=reverse)
        return self

    def limit(self, count: int) -> "LocalCursor":
        self.items = self.items[:count]
        return self

    async def to_list(self, length: int | None = None) -> list[dict]:
        if length is None:
            return deepcopy(self.items)
        return deepcopy(self.items[:length])


class LocalCollection:
    def __init__(self, name: str):
        self.path = storage_dir / f"{name}.json"
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to read {self.path}: {e}")
            return []

    def _write(self, items: list[dict]) -> None:
        try:
            self.path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        except (IOError, OSError) as e:
            logger.error(f"Failed to write {self.path}: {e}")
            raise

    @staticmethod
    def _matches(item: dict, query: dict) -> bool:
        return all(item.get(key) == value for key, value in query.items())

    @staticmethod
    def _project(item: dict, projection: dict | None) -> dict:
        if not projection:
            return deepcopy(item)

        include_fields = [key for key, value in projection.items() if value]
        if not include_fields:
            return deepcopy(item)
        return {key: item[key] for key in include_fields if key in item}

    async def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        for item in self._read():
            if self._matches(item, query):
                return self._project(item, projection)
        return None

    async def insert_one(self, document: dict) -> InsertOneResult:
        items = self._read()
        items.append(deepcopy(document))
        self._write(items)
        inserted_id = document.get("_id") or document.get("username") or document.get("timestamp")
        return InsertOneResult(inserted_id=inserted_id)

    async def delete_one(self, query: dict) -> dict:
        items = self._read()
        deleted = 0
        remaining = []
        for item in items:
            if not deleted and self._matches(item, query):
                deleted = 1
                continue
            remaining.append(item)
        self._write(remaining)
        return {"deleted_count": deleted}

    async def delete_many(self, query: dict) -> dict:
        items = self._read()
        remaining = [item for item in items if not self._matches(item, query)]
        deleted_count = len(items) - len(remaining)
        self._write(remaining)
        return {"deleted_count": deleted_count}

    def find(self, query: dict, projection: dict | None = None) -> LocalCursor:
        items = [
            self._project(item, projection)
            for item in self._read()
            if self._matches(item, query)
        ]
        return LocalCursor(items)

    def aggregate(self, pipeline: list[dict]) -> LocalCursor:
        items = self._read()
        for stage in pipeline:
            if "$match" in stage:
                query = stage["$match"]
                items = [item for item in items if self._matches(item, query)]
            elif "$group" in stage:
                grouped = {}
                group_spec = stage["$group"]["_id"]
                for item in items:
                    group_id = {
                        key: item.get(field_name.lstrip("$"))
                        for key, field_name in group_spec.items()
                    }
                    grouped[json.dumps(group_id, sort_keys=True)] = {"_id": group_id}
                items = list(grouped.values())
            elif "$sort" in stage:
                sort_spec = stage["$sort"]
                for field, direction in reversed(list(sort_spec.items())):
                    sort_key = field.replace("_id.", "")
                    reverse = direction < 0
                    items.sort(key=lambda item: item.get("_id", {}).get(sort_key, ""), reverse=reverse)
        return LocalCursor(items)


class LocalDatabase:
    def __init__(self):
        self.users = LocalCollection("users")
        self.refresh_sessions = LocalCollection("refresh_sessions")
        self.occupancy_logs = LocalCollection("occupancy_logs")


database = LocalDatabase()
mongodb_instance = None


async def get_database():
    """Get database instance (local JSON or MongoDB based on settings)."""
    global mongodb_instance
    
    if settings.enable_mongodb:
        try:
            from .mongodb_db import get_mongodb
            if mongodb_instance is None:
                mongodb_instance = await get_mongodb()
            return mongodb_instance
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB, falling back to local JSON: {e}")
            return database
    return database
