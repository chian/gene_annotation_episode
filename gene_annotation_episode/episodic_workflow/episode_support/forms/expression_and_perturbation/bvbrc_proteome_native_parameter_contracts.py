from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
_FAILURES = (('bundle_invalid application_mismatch original_task_conflict', 'original_task', None, 'association'), ('parameters_invalid requested_form_invalid source_contract_incompatible', 'parser_binding', 'proteome_native_projection', 'publication'), ('document_missing primary_document_missing artifact_bytes_missing', 'output_bytes', 'proteome_native_projection', 'association'), ('document_ambiguous primary_document_invalid artifact_format_incompatible nonzero_range_unsupported', 'parser_binding', 'proteome_native_projection', 'association'), ('artifact_digest_mismatch artifact_binding_conflict', 'byte_version_evidence', 'proteome_native_projection', 'association'), ('supplied_data_missing supplied_data_ambiguous supplied_data_invalid', 'scientific_metadata', 'proteome_supplied_data', 'association'), ('input_bytes_missing input_binding_missing input_binding_ambiguous', 'input_bytes', 'proteome_supplied_input', 'association'), ('parameter_source_unbound parameter_source_conflict', 'original_task', 'proteome_original_input_index', 'association'), ('completeness_evidence_unverified parsed_construction_evidence_unverified', 'byte_version_evidence', 'proteome_supplied_input', 'association'), ('supplied_source_conflict source_field_unbound', 'scientific_metadata', 'proteome_supplied_input', 'association'), ('deployment_evidence_unverified', 'byte_version_evidence', 'proteome_native_projection', 'association'), ('parsed_result_invalid parsed_result_mismatch supplied_reader_incompatible', 'parser_binding', 'proteome_supplied_input', 'native_decode'), ('projection_parameters_invalid projection_requested_form_invalid', 'parser_binding', 'proteome_requested_projection', 'publication'), ('saved_sheet_invalid saved_components_invalid saved_identity_conflict saved_projection_conflict', 'parser_binding', 'proteome_requested_projection', 'return'), ('requested_target_missing requested_target_ambiguous requested_value_unavailable requested_population_unavailable requested_reference_unresolved', 'scientific_metadata', 'proteome_requested_projection', 'publication'))
BINDING_DETAILS = {'proteome_' + name: (kind, role, phase) for names, kind, role, phase in _FAILURES for name in names.split()}
BINDING_CODES = frozenset(BINDING_DETAILS)

class ProteomeNativeBundleError(ValueError):
    """Finite public failure identity and exact JSON pointer, without source prose."""

    def __init__(self, code: str, path: str=''):
        if code not in BINDING_CODES:
            raise ValueError('unknown_proteome_bundle_failure_code')
        self.code, self.path = (code, path)
        super().__init__(code)

def _require(condition, code, path=''):
    if not condition:
        raise ProteomeNativeBundleError(code if code.startswith('proteome_') else 'proteome_' + code, path)
_DOCUMENT = json.loads(Path(__file__).with_name('bvbrc_proteome_native_bundle_schemas.json').read_text(encoding='utf-8'))

@lru_cache(maxsize=None)
def _schema(name):
    definitions, reachable = (_DOCUMENT['$defs'], set())
    _require(type(name) is str and name in definitions, 'parameters_invalid')

    def visit(node):
        if type(node) is dict:
            if '$ref' in node:
                key = node['$ref'][8:]
                if not node['$ref'].startswith('#/$defs/') or key not in definitions:
                    raise RuntimeError('invalid_packaged_proteome_bundle_reference')
                if key not in reachable:
                    reachable.add(key)
                    visit(definitions[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)
    root = {'$schema': _DOCUMENT['$schema'], '$ref': '#/$defs/' + name}
    visit(root)
    root['$defs'] = {key: definitions[key] for key in definitions if key in reachable}
    return root
