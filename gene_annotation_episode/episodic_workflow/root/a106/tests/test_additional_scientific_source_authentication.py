"""Actual additional A106 prospective source gates; no model/native workflow.

These checks authenticate current source bytes and tamper rejection. They do not
establish compatibility with an older emitted scientific Store or saved roster.
"""
import hashlib
from importlib import import_module
import pytest

from ..state import Store

AXIS=__package__.rsplit('.tests',1)[0]
CASES=(
    ('kinetic',None,'_dependencies','_SOURCE_LOCATION_FROZEN'),
    ('endpoint_signal','LiteratureEndpointSignalRepository','_original_implementation','_PURE_HASHES'),
    ('ion_discrimination','LiteratureIonDiscriminationRepository','_implementation_receipt','_FROZEN'),
    ('product_coupling','LiteratureProductCouplingRepository','_implementation_receipt','_FROZEN'),
    ('measurement_validation','LiteratureMeasurementValidationRepository','_implementation_receipt','_FROZEN'),
    ('measurement_comparison','LiteratureMeasurementComparisonRepository','_original_implementation','_PURE_HASHES_V3'),
    ('concentration_window','LiteratureConcentrationWindowRepository','_original_implementation','PURE_HASHES'),
)


@pytest.mark.parametrize('family,class_name,method,pins',CASES)
def test_additional_original_current_source_gate_and_byte_tamper(
        tmp_path,monkeypatch,family,class_name,method,pins):
    module=import_module(AXIS + '.library.literature_' + family + '_storage')
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='ATGGCT',molecule='dna')
        owner=module if class_name is None else getattr(module,class_name)(store,'source-authentication')
        read=getattr(owner,method)
        receipt=read()
        files=receipt['sha256'] if 'sha256' in receipt else receipt['files']
        assert files
        assert all(hashlib.sha256(module.source_file(name).read_bytes()).hexdigest()==digest
                   for name,digest in files.items())
        chosen=next(iter(getattr(module,pins)))
        original=module.source_file
        changed=tmp_path/chosen
        changed.write_bytes(original(chosen).read_bytes()+b'\n# unapproved scientific source mutation\n')
        monkeypatch.setattr(module,'source_file',lambda name:changed if name==chosen else original(name))
        with pytest.raises(module.ContractError,match='dependency_mismatch'):
            read()
