from dataclasses import dataclass
from datetime import datetime


@dataclass
class FetchResponse:
    source: str
    fetched_at: datetime
    payload: dict


@dataclass
class SQLQuery:
    table: str
    conflict_key: str
    fields: dict
