"""Compare retained pure fixture outputs with current explicit re-execution.

This is not storage reconstruction or hidden reacquisition through a calculator.
"""
from pathlib import Path
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('measurement_validation_tests205',ROOT/'tests/test_literature_measurement_validation_205.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
retained=json.loads((OUT/'PURE_SOURCE_EXAMPLES_003.json').read_text())
for i,prior in enumerate(retained['examples']):
    source,args,rows,fields=fixture.original(i)
    data,sheet=fixture.run(source,args,rows)
    assert fields==prior['source_fields'] and args==prior['selection']
    assert rows==prior['possessed_recovery_rows_fixture'] and sheet==prior['sheet']
print(json.dumps({'current_pure_outputs_equal_retained_examples':3,'implicit_source_IO_in_calculator':False,
    'storage_reconstruction_verified':False,'episode_execution_verified':False}))
