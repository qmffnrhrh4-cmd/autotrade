from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging


class BaseManager(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.enabled = True
        self.initialized = False
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self._stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0
        }

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'enabled': self.enabled,
            'initialized': self.initialized,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            **self._stats
        }

    def reset_stats(self):
        self._stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0
        }
        self.logger.info(f"{self.name} stats reset")

    def enable(self):
        self.enabled = True
        self.logger.info(f"{self.name} enabled")

    def disable(self):
        self.enabled = False
        self.logger.info(f"{self.name} disabled")

    def _increment_stat(self, key: str, amount: int = 1):
        if key in self._stats:
            self._stats[key] += amount
            self.last_updated = datetime.now()

    def _record_operation(self, success: bool):
        self._increment_stat('total_operations')
        if success:
            self._increment_stat('successful_operations')
        else:
            self._increment_stat('failed_operations')

    @property
    def success_rate(self) -> float:
        total = self._stats['total_operations']
        if total == 0:
            return 0.0
        return (self._stats['successful_operations'] / total) * 100

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, enabled={self.enabled})>"
