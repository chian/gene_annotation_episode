from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation import bvbrc_proteome_native_parameter_contracts as native_layer
_FAILURES = (('document_missing', 'output_bytes', 'proteome_directional_report', 'association'), ('document_ambiguous duplicate_document_selection', 'parser_binding', 'proteome_directional_report', 'association'), ('artifact_binding_conflict artifact_digest_mismatch', 'byte_version_evidence', 'proteome_directional_report', 'association'), ('format_incompatible nonzero_range_unsupported declared_version_conflict', 'parser_binding', 'proteome_directional_report', 'association'), ('reader_contract_invalid sheet_construction_failed calculation_failed', 'parser_binding', 'proteome_directional_report', 'native_decode'), ('requested_target_missing requested_value_unavailable', 'scientific_metadata', 'proteome_requested_projection', 'publication'), ('saved_identity_conflict saved_numerical_relationship_conflict', 'parser_binding', 'proteome_requested_projection', 'return'))
DIRECTIONAL_BINDING_DETAILS = {'proteome_directional_' + name: (kind, role, phase) for names, kind, role, phase in _FAILURES for name in names.split()}
DIRECTIONAL_BINDING_CODES = frozenset(DIRECTIONAL_BINDING_DETAILS)
DIRECTIONAL_BINDING_INPUT_KINDS = {name: value[0] for name, value in DIRECTIONAL_BINDING_DETAILS.items()}
BINDING_DETAILS = {**native_layer.BINDING_DETAILS, **DIRECTIONAL_BINDING_DETAILS}
BINDING_CODES = frozenset(BINDING_DETAILS)

class ProteomeBundleError(ValueError):

    def __init__(self, code, path=''):
        if code not in BINDING_CODES:
            raise ValueError('unknown_proteome_bundle_failure_code')
        self.code, self.path = (code, path)
        super().__init__(code)

def _require(condition, code='proteome_directional_saved_identity_conflict', path=''):
    if not condition:
        raise ProteomeBundleError(code, path)
_DOCUMENT = json.loads(Path(__file__).with_name('bvbrc_proteome_bundle_schemas.json').read_text(encoding='utf-8'))

@lru_cache(maxsize=None)
def _schema(name):
    definitions, reached = (_DOCUMENT['$defs'], set())
    _require(name in definitions, 'proteome_parameters_invalid', '/name')

    def visit(node):
        if type(node) is dict:
            if '$ref' in node:
                key = node['$ref'].removeprefix('#/$defs/')
                if key not in definitions:
                    raise RuntimeError('invalid_packaged_proteome_reference')
                if key not in reached:
                    reached.add(key)
                    visit(definitions[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)
    root = {'$schema': _DOCUMENT['$schema'], '$ref': '#/$defs/' + name}
    visit(root)
    root['$defs'] = {k: v for k, v in definitions.items() if k in reached}
    return root

def bundle_schema(name):
    return deepcopy(_schema(name))

def parameters_schema():
    return bundle_schema('ProviderParameters')
