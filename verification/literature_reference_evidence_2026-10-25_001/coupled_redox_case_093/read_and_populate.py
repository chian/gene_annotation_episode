"""Execute existing readers and new bound arithmetic on retained primary HTML.

One paper, explicitly reviewed experimental meanings. No model or network
acquisition, native episode, controller action, or annotation credit is used.
Creates fresh output files once; historical case031 is never rewritten.
"""
from copy import deepcopy
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sys
from fractions import Fraction

from gene_annotation_episode.literature_experimental_contracts import HEADERS
from gene_annotation_episode.literature_rate_reader import read_rate_table
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_rate_bound_calculations import populate_rate_table_bounds
from gene_annotation_episode.literature_optical_inputs import read_optical_rate_operands
from gene_annotation_episode.literature_optical_calculations import calculate_nadh_optical_rate
from gene_annotation_episode.literature_optical_validation import validate_optical_selection


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
if len(sys.argv)>1:
    assert len(sys.argv)==2 and re.fullmatch(r'generation_[0-9]{3}',sys.argv[1])
    OUT=OUT/sys.argv[1];OUT.mkdir(exist_ok=False)
SOURCE = ROOT/'research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary_access_0.bin'
raw = SOURCE.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
assert sha == '318ac6fe96b509815001892dcaa996688c703175c7dedf88b663d99fe9c90bcf'
text = raw.decode('utf-8')
source_ref, artifact_ref = 'source_'+sha[:24], 'artifact_'+sha


def witness(start, end):
    return dict(source_ref=source_ref, representation='original',
        start=len(text[:start].encode()), end=len(text[:end].encode()), quote=text[start:end])


def locate(quote, start=0, end=None):
    first = text.index(quote, start, len(text) if end is None else end)
    return witness(first, first+len(quote))


def save(name, value):
    with (OUT/name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


class Table2(HTMLParser):
    """Finite HTML-table extraction with original byte spans for every cell."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections, self.rows, self.row, self.cell = [], [], None, None
        self.active = False
        self.section_start = self.section_end = None
        self.starts = [0]
        self.starts += [m.end() for m in re.finditer('\n', text)]

    def position(self):
        line, column = self.getpos()
        return self.starts[line-1]+column

    def handle_starttag(self, tag, attrs):
        if tag == 'section':
            self.sections.append(dict(attrs).get('id'))
            if self.sections[-1] == 't2': self.section_start = self.position()
        if tag == 'table' and 't2' in self.sections: self.active = True
        if not self.active: return
        if tag == 'tr': self.row = []
        if tag in ('td','th'):
            self.cell = dict(start=self.position(), text=[])
        elif self.cell is not None and tag in ('p','div','br'):
            self.cell['text'].append(' ')

    def handle_data(self, data):
        if self.active and self.cell is not None: self.cell['text'].append(data)

    def handle_endtag(self, tag):
        if self.active and tag in ('td','th') and self.cell is not None:
            end = text.index('>', self.position())+1
            self.row.append(dict(text=' '.join(''.join(self.cell['text']).split()),
                                 witness=witness(self.cell['start'], end)))
            self.cell = None
        if self.active and tag == 'tr': self.rows.append(self.row); self.row = None
        if tag == 'table': self.active = False
        if tag == 'section':
            if self.sections[-1] == 't2': self.section_end = text.index('>',self.position())+1
            self.sections.pop()


parser = Table2(); parser.feed(text)
assert parser.rows[0][0]['text'] == 'Assay mixturea'
assert parser.rows[0][1]['text'] == 'Sp act (U/mg)'
headings = {
    'NADH oxidation (measured photometrically)': ('nadh',25,'NADH oxidation'),
    'TTC reduction (measured photometrically)': ('ttc',25,'TTC reduction'),
    'Ferredoxin reduction (measured via H2 formation in the presence of hydrogenase)': ('h2',37,'H2 formation'),
}
stream = io.StringIO(newline='')
writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
writer.writerow(HEADERS)
locations, scopes, records = [], {}, {}
current = None
for row in parser.rows[1:]:
    if row[0]['text'] in headings:
        assert all(not cell['text'] for cell in row[1:])
        current = headings[row[0]['text']]
        scopes[current[0]] = row[0]
        continue
    assert current is not None and len(row) == 2
    assay, temperature, endpoint = current
    match = re.fullmatch(r'([<>]?\s*[0-9]+(?:\.[0-9]+)?)(?:\s*\(([0-9]+(?:\.[0-9]+)?)\))?([a-z]?)', row[1]['text'])
    assert match is not None, row[1]['text']
    values = [(temperature, match[1], False)]
    if match[2] is not None:
        # The paper's explicit footnote and Results identify parentheses as37C.
        # Retain the printed marker; do not silently repair its a/b mismatch.
        values.append((37, match[2], True))
    for temp, value, parenthetical in values:
        arm = f'{assay}@{temp}|{row[0]["text"]}'
        condition = f'{assay} assay at {temp}C; {row[0]["text"]}'
        writer.writerow(('C. kluyveri DSM555 purified Bcd/Etf complex', 'PMC2223550 Table2',
            arm, condition, endpoint, 'per mg purified complex', value, 'umol/min/mg',
            'unreported', '', '', 'unspecified', 'reported'))
        locations.append(dict(mapped_row=len(locations)+2, arm=arm, assay_heading=scopes[assay],
            mixture_cell=row[0], value_cell=row[1], temperature_C=temp,
            parenthetical=parenthetical, printed_marker=match[3] or None,
            origin='reported', sampling_count=None, sampling_uncertainty=None))
        records[arm] = condition
table_text = stream.getvalue()
assert len(locations) == 21
with (OUT/'MAPPED_TABLE.tsv').open('x') as file: file.write(table_text)
mapped_sha = hashlib.sha256(table_text.encode()).hexdigest()
table = dict(source_ref='source_'+mapped_sha[:24], artifact_ref='artifact_'+mapped_sha,
             text=table_text, delimiter='\t', representation='retained_extraction')
extraction = read_rate_table(table,
    expected_subject='C. kluyveri DSM555 purified Bcd/Etf complex', expected_experiment='PMC2223550 Table2')
save('PRIMARY_TABLE_CUSTODY.json', dict(source_path=str(SOURCE.relative_to(ROOT)), source_sha256=sha,
    primary_source_ref=source_ref, primary_artifact_ref=artifact_ref,
    source_url='https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/',
    table_context_and_unit_definitions=witness(parser.section_start,parser.section_end),
    mapped_table_sha256=mapped_sha, mapped_table_source_ref=table['source_ref'],
    rows=locations, interpretation_origin='root scientific conversion after full post-paper reset',
    table_rows_are_reported_summaries_not_raw_replicates=True))
save('RATE_EXTRACTION.json', extraction)
comparisons = {}
for assay, temp, reference_label, test_label, name in (
    ('nadh',25,'Fd + Hyd','Fd + Hyd − crotonyl-CoA','nadh_crotonyl_omission'),
    ('ttc',25,'TTC','TTC − crotonyl-CoA','ttc_crotonyl_omission'),
    ('h2',37,'Fd + Hyd','Fd + Hyd − crotonyl-CoA','h2_crotonyl_omission'),
    ('nadh',25,'Fd + Hyd','Fd + Hyd − FAD','nadh_fad_omission'),
    ('h2',37,'Fd + Hyd','Fd + Hyd − FAD','h2_fad_omission'),
    ('nadh',25,'Fd + Hyd','Fd + Hyd + methyl viologen','nadh_methyl_viologen'),
    ('h2',37,'Fd + Hyd','Fd + Hyd + methyl viologen','h2_methyl_viologen')):
    a, b = f'{assay}@{temp}|{reference_label}', f'{assay}@{temp}|{test_label}'
    args = dict(reference_arm=a, test_arm=b, reference_condition=records[a], test_condition=records[b])
    # The original point/statistical calculator is retained beside the new
    # constraint image; a new bound is not a fabricated source point/likelihood.
    comparisons[name] = dict(constraint=populate_rate_table_bounds(extraction, **args),
                             point=populate_rate_contrast(extraction, **args))
assert Fraction(comparisons['nadh_crotonyl_omission']['constraint']['cells']['fractional_decrease']['lower']) <= Fraction(699,700)
assert comparisons['nadh_crotonyl_omission']['constraint']['cells']['fractional_decrease']['lower_closed'] is False
assert comparisons['ttc_crotonyl_omission']['constraint']['cells']['fractional_decrease']['value'] == .95
assert Fraction(comparisons['h2_crotonyl_omission']['constraint']['cells']['fractional_decrease']['lower']) <= Fraction(499,500)
assert comparisons['nadh_crotonyl_omission']['point']['cells']['fractional_decrease']['value'] is None
assert all(item['point']['cells']['source_signed_index']['value'] is None for item in comparisons.values())
save('POPULATED_CONTRASTS.json', comparisons)
a, b = 'nadh@37|Fd + Hyd', 'h2@37|Fd + Hyd'
cross = populate_rate_table_bounds(extraction, reference_arm=a, test_arm=b,
    reference_condition=records[a], test_condition=records[b])
assert cross['cells']['reference_rate']['value'] == 14 and cross['cells']['test_rate']['value'] == 5
assert cross['cells']['retained_fraction']['unavailable_reason'] == 'endpoint_mismatch'
save('CROSS_ENDPOINT_LIMIT.json', cross)

# Exercise the existing optical reader on the actual reported coefficient.
method_start = text.index('NADH oxidation catalyzed')
pstart = text.rfind('<p',0,method_start); pend = text.index('</p>',method_start)+4
protocol = witness(pstart,pend)
epsilon = locate('6.2',pstart,pend)
epsilon_unit = locate('mM<sup>−1</sup> cm<sup>−1</sup>',pstart,pend)
measured = locate('NADH',method_start,pend)
quantity = dict(measurement_identity=protocol, condition=protocol, measured_entity=measured,
    interval=None, measurement=dict(number=dict(witness=epsilon,number_start=0,number_end=3), unit=epsilon_unit),
    qualification=dict(value='reported_point',witnesses=[protocol]))
unknown = dict(value='unknown',witnesses=[])
selection = dict(source_ref=source_ref,source_kind='primary_source',
    molecule=locate('butyryl-CoA dehydrogenase/Etf complex',pstart,pend),construct=None,preparation=None,
    condition=protocol,measured_entity=measured,
    signal_kind=deepcopy(unknown),relation=dict(value='applicable_extinction_relation',witnesses=[protocol]),
    blank_role=deepcopy(unknown),same_endpoint=deepcopy(unknown),matched_window=deepcopy(unknown),
    rate_window=deepcopy(unknown),signals=dict(sample=None,blank=None),
    calibration=dict(epsilon=quantity,path_length=None,wavelength=None),covariance_source_ref=None)
calls=[]
def read_source(reference,representation):
    assert (reference,representation)==(source_ref,'original')
    calls.append((reference,representation))
    return dict(content=raw,artifact_ref=artifact_ref)
optical=read_optical_rate_operands(selection,read_source=read_source)
assert len(calls)==1
assert optical['calibration']['epsilon']['value']==6.2
assert optical['calculation_inputs']['path_length'] is None
assert validate_optical_selection(selection,json.loads(json.dumps(optical)))==selection
optical_cells=calculate_nadh_optical_rate(optical['calculation_inputs'])
assert optical_cells['net_depletion_rate']['value'] is None
assert optical_cells['net_depletion_rate']['unavailable_reason']=='missing_sample_slope'
save('OPTICAL_PARTIAL.json',dict(selection=selection,extraction=optical,cells=optical_cells,
    read_source_calls=calls,wavelength_note='Source epsilon subscript340 retained in protocol; no separate nm quantity supplied',
    calibration_recovery=None,trace_slope=None,path_length=None,sampling_covariance=None))
save('RESULTS.json',dict(primary_reported_measurements=len(locations),assay_readouts=['NADH oxidation','TTC reduction','H2 formation'],
    numerical_comparisons=len(comparisons),reported_constraint_bound_checks=3,optical_coefficient=6.2,
    optical_de_novo_rate=None,calibration_recovery=None,independent_preparation_count=None,
    primary_files_modified=False,native_episode_executed=False,model_calls=0,controller_observations_added=0,
    aggregate_assay_reliability=None,completed_assay_specific_graders=0))
print('Retained21 reported rate summaries from20 primary Table2 rows, including the separate37C parenthetical value.')
print('Executed seven within-endpoint comparisons; strict omission fractions >699/700, .95, >.998.')
print('Actual optical reader retained epsilon6.2; missing slope/path/calibration recovery remain unknown.')
