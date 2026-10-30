"""Inspect only existing schemas; no source, Store, provider or numerical work."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def counts(node):
    result = {'witness_nodes': 0, 'witness_descriptions': 0, 'number_selector_nodes': 0,
              'number_selector_descriptions': 0, 'definition_nodes': 0, 'definition_descriptions': 0}
    def visit(value):
        if isinstance(value, dict):
            fields = value.get('properties', {})
            category = ('witness' if set(fields) == {'source_ref', 'representation', 'start', 'end', 'quote'}
                else 'number_selector' if set(fields) == {'witness', 'number_start', 'number_end'}
                else 'definition' if set(fields) == {'bridge', 'clause', 'amount', 'amount_unit', 'time_unit',
                    'endpoint', 'endpoint_entity', 'definition_entity'} else None)
            if category:
                result[category + '_nodes'] += 1
                result[category + '_descriptions'] += 'description' in value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(node)
    return result


def main():
    from gene_annotation_episode.literature_episodes import _population_catalog
    from gene_annotation_episode.literature_partner_native_inputs import partner_source_population_schema
    catalog = _population_catalog()
    partner = next(row for row in catalog if row['name'] == 'literature.partner.source.populate')
    rate = next(row for row in catalog if row['name'] == 'literature.rate.source.populate')
    assert partner['input_schema'] == partner_source_population_schema()
    partner_counts, rate_counts = counts(partner['input_schema']), counts(rate['input_schema'])
    assert partner_counts['definition_descriptions'] == 0 and rate_counts['definition_descriptions'] > 0
    result = {'scope': 'Actual current catalog schema information only; no claim about any scientific argument chosen by a model',
        'operations': len(catalog), 'partner': partner_counts, 'rate': rate_counts,
        'partner_catalog_is_exact_bare_native_schema': True,
        'opportunity': 'Expose equally complete operand instructions for the actual partner route without relaxing reader validation or changing TASK/science/numbers',
        'source_or_model_or_Store_work': False, 'runtime_observations': 0,
        'causal_claim_that_missing_descriptions_explain_live_failures': False}
    with (HERE / 'PARTNER_INFORMATION_GAP_RECEIPT_007.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
