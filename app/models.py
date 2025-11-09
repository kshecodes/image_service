from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

ISO = "%Y-%m-%dT%H:%M:%SZ"

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO)

@dataclass
class CreateImageRequest:
    user_id: str
    content_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Body must be a JSON object")
        user_id = data.get("user_id")
        content_type = data.get("content_type")
        if not user_id or not content_type:
            raise ValueError("'user_id' and 'content_type' are required")
        tags = data.get("tags") or []
        if not isinstance(tags, list):
            raise ValueError("'tags' must be a list of strings")
        return cls(
            user_id=user_id,
            content_type=content_type,
            title=data.get("title"),
            description=data.get("description"),
            tags=tags,
        )
