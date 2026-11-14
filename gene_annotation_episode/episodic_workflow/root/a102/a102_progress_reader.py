"""A102 saved progress reader for its resource and monitor bindings."""
from dataclasses import dataclass

from .episode_monitoring import read_progress


@dataclass(frozen=True)
class SavedProgressReader:
    store: object
    run_id: str

    def read_progress(self, reference, scope):
        return read_progress(self.store, self.run_id, reference, scope)
