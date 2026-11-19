"""The root's report: the annotated subject, each axis credit and return, and the hypervolume credit."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import json

from episode_runtime import Field, RecordForm
from method_loop import ClosedRecord

from .continuation import AnnotationState

RETURN_FORM = RecordForm({
    'subject': Field('record', 'The annotated subject, as its admitted Store scope'),
    'axis_credits': Field('record', 'Each axis credit, on its own unbounded scale'),
    'findings': Field('list', 'Each commissioned axis return: axis, credit, finding and progress receipt'),
    'credit': Field('number', 'The weighted offset-product hypervolume over the nine axis credits'),
})


@dataclass(frozen=True)
class Record(ClosedRecord):
    """A closed JSON record of the root's own."""
    value: Mapping

    def as_record(self):
        return json.loads(json.dumps(dict(self.value), sort_keys=True, allow_nan=False))


def build_report(subject, record):
    """The root result from the closed iteration ``record``: exactly ``RETURN_FORM``."""
    state = record.controller_state
    if not isinstance(state, AnnotationState):
        raise TypeError('annotation_report_requires_controller_state')
    return Record({'subject': subject, 'axis_credits': dict(state.axis_credits),
                   'findings': [unit.controller_input.as_record() for unit in record.unit_records],
                   'credit': state.credit})


__all__ = ['RETURN_FORM', 'Record', 'build_report']
