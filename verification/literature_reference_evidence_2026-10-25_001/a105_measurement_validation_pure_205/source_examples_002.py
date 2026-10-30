"""Owned reproducible pure source fixture; no Store/provider/episode execution."""
from pathlib import Path
import importlib.util
import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('measurement_validation_tests205', ROOT/'tests/test_literature_measurement_validation_205.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
examples = []
for row_index in range(3):
    source, arguments, received_rows, fields = fixture.original(row_index)
    inputs, sheet = fixture.run(source, arguments, received_rows)
    comparisons = []
    with localcontext() as ctx:
        ctx.prec = 65
        n, m = Decimal(fields['nominal']), Decimal(fields['measured'])
        for basis, row in zip(('within_run', 'between_run'), sheet['precision']):
            c = Decimal(fields[basis + '_CV_percent'])/100
            independent = ((m-n)**2 + (c*m)**2)/n**2
            loss = row['cells']['relative_squared_deviation_plugin']
            exact = Fraction(int(loss['conditional_exact_value']['numerator']), int(loss['conditional_exact_value']['denominator']))
            discrepancy = abs(Decimal(exact.numerator)/Decimal(exact.denominator)-independent)
            assert discrepancy < Decimal('1e-61')
            assert loss['value'] is None and loss['status']=='conditional'
            comparisons.append({'basis':basis, 'independent_decimal_loss':str(independent),
                'independent_decimal_RMS_percent':str(100*independent.sqrt()),
                'fraction_decimal_absolute_difference':str(discrepancy),
                'interpreted_value_unavailable':True})
    examples.append({'source_fields':fields, 'selection':arguments,
        'possessed_recovery_rows_fixture':received_rows, 'sheet':sheet, 'oracle_comparisons':comparisons})
result = {'kind':'controlled_pure_source_and_possessed_row_fixture',
    'source_sha256':hashlib.sha256(source.content).hexdigest(),
    'measurement_validation_version':sheet['version'],
    'original_source_rows':3, 'independent_Fraction_Decimal_comparisons':6,
    'examples':examples,
    'limits':['Actual original XML numeric spans and source meanings selected under explicit controlled caller interpretations.',
        'Recovery rows generated through existing pure recovery reader/calculator/projector and passed only as two controlled possessed rows.',
        'No Store, durable selected operation, provider/model, child/parent boundary, episode/controller or final credit executed.',
        'Source population, displayed CV denominator and recovery-context relationships remain unknown; conditional arithmetic is not a supported interpreted error estimate.',
        'No raw control, WST fit/sample blank conversion, product coupling or full A105 adequacy established.']}
with (OUT/'PURE_SOURCE_EXAMPLES_002.json').open('x') as stream:
    json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({'original_rows':3,'independent_comparisons':6,'source_sha256':result['source_sha256'],
    'interpreted_losses_available':sum(x['sheet']['precision'][0]['cells']['relative_squared_deviation_plugin']['value'] is not None for x in examples)}))
