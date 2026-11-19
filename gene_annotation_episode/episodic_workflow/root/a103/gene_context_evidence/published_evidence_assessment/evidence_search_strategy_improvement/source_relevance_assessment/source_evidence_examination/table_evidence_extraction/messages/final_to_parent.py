"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: controlled values only (``INVESTIGATION_FINDING_FEATURES_a103.md``
section B, option D-a; A103 has no literature grading sheet). The model's ``report`` names, from fixed vocabularies,
whether the source subject corresponds to the target and which kind of gene-context evidence the readings report,
and the exact readings (source, rows of a sheet or bytes of a table) it rests on; code reads the finding from that report:
the two choices, the number of readings, the row or byte extent they cover (so the next selection does not repeat it) and
the readings' sources. No quotation and no model-written text is returned. Nothing is selectable."""
from method_loop import ChoiceField, Field, RecordForm

CORRESPONDENCE = ('established', 'unresolved', 'not_applicable')
EVIDENCE_TYPES = ('conserved_neighborhood', 'gene_fusion', 'phylogenetic_cooccurrence', 'context_channel_association',
                  'context_contrast', 'single_locus_organization', 'none_applicable')
KINDS = ('sheet_rows', 'table_bytes')

READING_FORM = RecordForm({
    'source_ref': Field('text', 'The held source the reading is from'),
    'kind': ChoiceField('text', 'What offset and limit count: matching sheet rows, or the bytes of an article XML '
                        'table', KINDS),
    'offset': Field('integer', 'The first row (sheet_rows) or byte (table_bytes) of the reading'),
    'limit': Field('integer', 'The number of rows or bytes of the reading'),
})
# What the model writes with the report tool (validated by this form; it stays inside the Episode).
REPORT_FORM = RecordForm({
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence the readings report', EVIDENCE_TYPES),
    'readings': Field('list', 'The separate source-bound readings the report rests on', items=READING_FORM),
})
FINDING_FORM = RecordForm({
    'reported': Field('boolean', 'Whether the episode reported; the other values are empty when not'),
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence reported', EVIDENCE_TYPES),
    'reading_count': Field('integer', 'The number of readings the report rests on'),
    'covered_offset': Field('integer', 'The first row or byte the readings cover'),
    'covered_limit': Field('integer', 'The extent from covered_offset to the end of the last reading'),
    'source_refs': Field('record_refs', "The readings' sources"),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled values of the reported readings', form=FINDING_FORM),
})


def finding_of(report):
    """The finding code reads from the latest report (``None`` before one)."""
    if report is None:
        return {'reported': False, 'target_correspondence': 'unresolved', 'evidence_type': 'none_applicable',
                'reading_count': 0, 'covered_offset': 0, 'covered_limit': 0, 'source_refs': []}
    readings = report['readings']
    start = min((row['offset'] for row in readings), default=0)
    end = max((row['offset'] + row['limit'] for row in readings), default=0)
    return {'reported': True, 'target_correspondence': report['target_correspondence'],
            'evidence_type': report['evidence_type'], 'reading_count': len(readings), 'covered_offset': start,
            'covered_limit': end - start,
            'source_refs': list(dict.fromkeys(row['source_ref'] for row in readings))}


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': summary['finding']}
