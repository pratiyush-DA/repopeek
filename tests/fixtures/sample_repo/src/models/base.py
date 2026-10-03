"""Base entity models for fixture repo."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class BaseEntity(ABC):
    """Abstract root entity."""
    id: str
    created_at: datetime

    @abstractmethod
    def validate(self) -> bool:
        """Validate entity state."""
        pass


class AuditableEntity(BaseEntity):
    """Entity tracking updated timestamps and operators."""
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    def validate(self) -> bool:
        """Validate auditable fields."""
        return bool(self.id)
