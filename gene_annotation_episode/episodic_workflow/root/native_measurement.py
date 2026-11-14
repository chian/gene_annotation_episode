"""Canonical root native execution measurement; original typed receipt definition."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from gene_annotation_episode.run_statistics import ExecutionClass, RunStatistic
MEASUREMENT_VERSION = 'native_execution_measurement_v1'

@dataclass(frozen=True)
class NativeMeasurement:
    """One measured physical execution, without command/output/science text.

    This receipt remains useful locally even when the separate history writer
    is unavailable. Identity comes from the actual reserved unit and dispatch,
    never from a rounded duration, an episode role or a renamed operation.
    """
    execution_class: ExecutionClass
    statistic: RunStatistic
    condition_capture: str

    def __post_init__(self):
        if type(self.execution_class) is not ExecutionClass or type(self.statistic) is not RunStatistic:
            raise TypeError('typed_native_execution_measurement_required')
        if self.condition_capture not in {'captured_before_submission', 'unavailable_before_submission'}:
            raise ValueError('completed_measurement_requires_original_condition_capture')
        if self.condition_capture == 'unavailable_before_submission' and self.statistic.condition_ref is not None:
            raise ValueError('unavailable_condition_must_remain_unknown')

    def as_record(self):
        return {'version': MEASUREMENT_VERSION, 'execution_class': asdict(self.execution_class), 'statistic': asdict(self.statistic), 'condition_capture': self.condition_capture}

    @classmethod
    def from_record(cls, value):
        if type(value) is not dict or set(value) != {'version', 'execution_class', 'statistic', 'condition_capture'} or value['version'] != MEASUREMENT_VERSION:
            raise ValueError('unsupported_native_execution_measurement')
        return cls(ExecutionClass(**value['execution_class']), RunStatistic(**value['statistic']), value['condition_capture'])
