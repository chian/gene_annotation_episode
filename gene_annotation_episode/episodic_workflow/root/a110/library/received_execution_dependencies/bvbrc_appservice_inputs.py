from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import validate_contract

class AppServiceInputError(ValueError):
    """A specific local failure, with the existing closed Failure projection."""

    def __init__(self, code, *, refs=(), pointers=()):
        self.code = code
        self.failure = validate_contract('Failure', {'code': code, 'phase': 'association', 'affected_refs': list(dict.fromkeys(refs)), 'affected_pointers': list(dict.fromkeys(pointers)), 'effect_outcome': 'not_sent', 'valid_record_refs': [], 'requirements': []})
        self.diagnostics = [{'code': code, 'path': pointer} for pointer in list(pointers) or ['']]
        super().__init__(code)

def _require(condition, code, *, refs=(), pointers=()):
    if not condition:
        raise AppServiceInputError(code, refs=refs, pointers=pointers)

class AppServiceInputs:

    def __init__(self, execution, *, records, custody, read_acquisition=None):
        _require(read_acquisition is None or callable(read_acquisition), 'appservice_acquisition_reader_invalid')
        _require(execution.store is records.store is custody.store and execution.run_id == records.run_id == custody.run_id, 'appservice_input_binding_conflict')
        self.execution, self.records, self.custody = (execution, records, custody)
        self.read_acquisition = read_acquisition
