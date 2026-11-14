"""Original incoming AppService schema data bound to the one A106 validator.

This selects a retained read document; it does not register an operation or
change the active caller's capability or publication schema.
"""
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_contracts import ContractValidationError, _contract_schema_document, _validate_contract_document
_DOCUMENT = json.loads(Path(__file__).with_name('bvbrc_appservice_schemas.json').read_text())

def contract_schema(name):
    return _contract_schema_document(_DOCUMENT, name)

def validate_contract(name, value):
    return _validate_contract_document(_DOCUMENT, name, value)
