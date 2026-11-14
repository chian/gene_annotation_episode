"""A106 covariance support display and authenticated source masking."""
from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.root.a106.domain import identity


_FORMULAS = {
    'perturbation_mean_variance': 'Va+Vb-2Cov_mean',
    'perturbation_variance_lower': 'covariance_inequality_variance_bound',
    'perturbation_variance_upper': 'covariance_inequality_variance_bound',
    'restoration_mean_variance': 'Va+Vb-2Cov_mean',
    'restoration_variance_lower': 'covariance_inequality_variance_bound',
    'restoration_variance_upper': 'covariance_inequality_variance_bound',
    'shared_contrast_covariance': 'Cov_WR-Cov_WK-Cov_KR+V_K',
}


def covariance_support_refs(value, records):
    """Mask only authenticated A106 covariance support in recognized contracts."""
    def selected(row):
        for qualifier in row.get('covariance_interpretations', ()):
            if not isinstance(qualifier, Mapping):
                continue
            for reference in qualifier.get('support_refs', ()):
                record = records.get(reference)
                if (not isinstance(record, Mapping) or record.get('record_type') != 'reference'
                        or record.get('origin') != 'tool' or record.get('reference_type') != 'literature_result'
                        or record.get('label') != 'Covariance interpretation support'):
                    continue
                anchor = record.get('anchor')
                if not isinstance(anchor, Mapping) or any(name not in anchor for name in (
                        'source_ref', 'artifact_ref', 'start', 'end', 'quote')):
                    continue
                expected = identity('perturbation_literal', {'field': 'covariance_support',
                    'first': qualifier.get('first'), 'second': qualifier.get('second'), **dict(anchor)})
                if record.get('accession') == expected and record.get('source_ref') == anchor['source_ref']:
                    yield reference
    if isinstance(value, Mapping):
        if value.get('evaluated_scope') == 'interpreted_reference_perturbation':
            name = value.get('component')
            if (name in _FORMULAS
                    and value.get('formula_code') == 'perturbation_summary_' + name + '_v2'):
                yield from selected(value)
            cells = value.get('cells')
            if isinstance(cells, Mapping):
                for name, formula in _FORMULAS.items():
                    row = cells.get(name)
                    if isinstance(row, Mapping) and row.get('formula') == formula:
                        yield from selected(row)
        for child in value.values():
            yield from covariance_support_refs(child, records)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from covariance_support_refs(child, records)


def covariance_meanings(parts, rows, records, *, section, table):
    """Render A106 covariance meanings using the root's generic table helpers."""
    records = records or {}
    rendered = []
    for row in rows:
        for covariance in row.get('covariance_interpretations', ()):
            support = []
            for reference in covariance['support_refs']:
                record = records.get(reference)
                support.append(record.get('label', 'anchored source support') if isinstance(record, Mapping)
                    else 'meaning unavailable in the received scientific records')
            rendered.append((row['component'], covariance['first'] + ',' + covariance['second'],
                covariance['selection'], covariance['kind'], covariance['interpretation_basis'] or 'unreported',
                covariance['variance_status'], covariance['use'], '; '.join(support) or 'none supplied'))
    if rendered:
        section(parts, 'Selected covariance meanings', table(('Component', 'Arm pair', 'Selection',
            'Covariance kind', 'Interpretation basis', 'Variance status', 'Component use', 'Source support'), rendered))
