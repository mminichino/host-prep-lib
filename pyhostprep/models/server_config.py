from enum import Enum
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field


class IndexMemoryOption(Enum):
    default = 0
    memopt = 1


class ServerConfig(BaseModel):
    name: str = "cbserver"
    rally_ip_address: Optional[str] = None
    ip_address: str
    external_ip_address: Optional[str] = None
    services: Sequence[str] = ("data", "index", "query")
    username: str = "Administrator"
    password: str = "password"
    index_mem_opt: IndexMemoryOption = IndexMemoryOption.default
    server_group: str = "group-1"
    data_path: str = "/opt/couchbase/var/lib/couchbase/data"
    community_edition: bool = False
    private_key: Optional[str] = None
    options: List[str] = Field(default_factory=list)

    @property
    def get_values(self):
        return {name: field.annotation for name, field in self.model_fields.items()}

    @property
    def as_dict(self):
        return self.model_dump()
