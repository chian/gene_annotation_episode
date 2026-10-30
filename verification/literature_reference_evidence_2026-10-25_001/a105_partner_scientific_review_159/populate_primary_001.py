"""Controlled primary-source selections, existing partner operations and returns.

Scientific roles and source selections are root-reviewed, not model-selected.
Numbers are parsed from retained source bytes by the existing readers. The
independent oracle is never supplied as a scientific tool operand.
"""
from pathlib import Path
import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import partial
from html.parser import HTMLParser
import hashlib
import json
import math
import re
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = ROOT / "verification/literature_reference_evidence_2026-10-25_001/a105_configured_return_scientific_review_155/pin_004"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_partner_storage import COMPONENTS, LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


class Tables(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.raw = text
        self.lines = [0]
        for match in re.finditer("\n", text):
            self.lines.append(match.end())
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, name, attrs):
        start = self.position()
        if name == 'table':
            if self.table is not None:
                raise RuntimeError('Nested table requires explicit source review')
            self.table = []
        elif self.table is not None and name == 'tr':
            self.row = {'start': start, 'cells': []}
        elif self.row is not None and name in ('td', 'th'):
            self.cell = {'start': start + len(self.get_starttag_text()), 'data': [], 'visible': ''}

    def handle_data(self, data):
        if self.cell is not None:
            self.cell['visible'] += data
            self.cell['data'].append((self.position(), data))

    def handle_endtag(self, name):
        start = self.position()
        if self.cell is not None and name in ('td', 'th'):
            self.cell['end'] = start
            self.row['cells'].append(self.cell)
            self.cell = None
        elif self.row is not None and name == 'tr':
            self.row['end'] = self.raw.index('>', start) + 1
            self.table.append(self.row)
            self.row = None
        elif self.table is not None and name == 'table':
            self.tables.append(self.table)
            self.table = None


def witness(text, source, start, end, representation):
    quote = text[start:end]
    assert quote
    return {'source_ref': source, 'representation': representation,
        'start': len(text[:start].encode()), 'end': len(text[:end].encode()), 'quote': quote}


def within(text, source, quote, lo=0, hi=None, representation='text'):
    start = text.index(quote, lo, len(text) if hi is None else hi)
    return witness(text, source, start, start + len(quote), representation)


def subset(text, source, outer, quote, *, last=False):
    start = outer['quote'].rindex(quote) if last else outer['quote'].index(quote)
    absolute = len(text.encode()[:outer['start']].decode()) + start
    return witness(text, source, absolute, absolute + len(quote), outer['representation'])


def selectors(raw_html, text, source):
    parsed = Tables(raw_html)
    parsed.feed(raw_html)
    candidates = [table for table in parsed.tables if table and any(
        'Sp act' in cell['visible'] for cell in table[0]['cells'])]
    assert len(candidates) == 1
    table = candidates[0]
    rows, section = {}, None
    for row in table:
        names = [re.sub(r'\s+', ' ', cell['visible']).strip() for cell in row['cells']]
        if len(names) == 1:
            if names[0].startswith('NADH oxidation'):
                section = 'nadh'
            elif names[0].startswith('TTC reduction'):
                section = 'ttc'
            elif names[0].startswith('Ferredoxin reduction'):
                section = 'h2'
        elif len(names) == 2 and section:
            rows[section, names[0]] = row

    heading = within(text, source, 'TABLE 2. Crotonyl-CoA-dependent NADH oxidation and ferredoxin reduction catalyzed by purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri')
    subject = within(text, source, 'purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri',
                     len(text.encode()[:heading['start']].decode()))
    normalization = within(text, source, 'Sp act (U/mg)', len(text.encode()[:heading['end']].decode()))
    unit_witness = subset(text, source, normalization, 'U/mg')
    bridge = within(text, source, 'One unit was equivalent to 1 μmol of NADH oxidized per min, 1 μmol of TTC reduced per min, or 1 μmol of H2 formed per min.')
    endpoints = {'nadh': within(text, source, 'NADH oxidation (measured photometrically)'),
        'h2': within(text, source, 'H2 formation', text.index('Ferredoxin reduction (measured via H2 formation'))}
    partners = {'Fd': within(text, source, 'Ferredoxin from Clostridium pasteurianum'),
        'Hyd': within(text, source, 'Hydrogenase from C. pasteurianum')}
    qualifications = [within(text, source, 'Both the absolute and relative values of the specific activities varied from preparation to preparation.'),
        within(text, source, 'Some of the reactions started with a considerable lag period, and the rates of the reactions were not always proportional to the amounts of enzyme added.')]

    def unit(endpoint):
        entity = 'NADH' if endpoint == 'nadh' else 'H2'
        clause = subset(text, source, bridge, '1 μmol of ' + entity + (' oxidized' if endpoint == 'nadh' else ' formed') + ' per min')
        return {'kind': 'source_defined_rate_unit', 'witness': unit_witness, 'definition': {
            'bridge': bridge, 'clause': clause,
            'amount': {'witness': clause, 'number_start': 0, 'number_end': 1},
            'amount_unit': subset(text, source, clause, 'μmol'),
            'time_unit': subset(text, source, clause, 'min', last=True),
            'endpoint': endpoints[endpoint], 'endpoint_entity': subset(text, source, endpoints[endpoint], entity),
            'definition_entity': subset(text, source, clause, entity)}}

    protocols = {}
    for endpoint, lead, end in (
        ('nadh', 'For NADH oxidation each 1-ml assay mixture', 'For TTC reduction each'),
        ('h2', 'For ferredoxin reduction each 0.5-ml assay mixture', 'The reactions were started'),
    ):
        lo = text.index(lead)
        hi = text.index(end, lo)
        protocols[endpoint] = (lo, hi)

    def conditions(endpoint, partner):
        lo, hi = protocols[endpoint]
        fragments = {
            'temperature': '25°C' if endpoint == 'nadh' else '37°C',
            'volume': '1-ml assay mixture' if endpoint == 'nadh' else '0.5-ml assay mixture',
            'buffer_and_pH': '50 mM Tris-HCl (pH 7.5)',
            'NADH': '0.1 mM NADH' if endpoint == 'nadh' else '2.5 mM NADH',
            'crotonyl_CoA': '0.1 mM crotonyl-CoA' if endpoint == 'nadh' else '1 mM crotonyl-CoA',
            'FAD': '5 μM FAD' if endpoint == 'nadh' else '10 μM FAD',
            'DTT': '2 mM DTT',
            'complex_amount': '0.01 mg purified butyryl-CoA dehydrogenase/Etf complex' if endpoint == 'nadh' else '0.05 mg purified butyryl-CoA dehydrogenase/Etf complex',
            'other_component': ('0.4 U hydrogenase' if endpoint == 'nadh' else '1.6 U hydrogenase') if partner == 'Fd' else
                ('20 μM ferredoxin' if endpoint == 'nadh' else '50 μM ferredoxin'),
        }
        factors = [{'factor': key, 'level': {'kind': 'literal', 'witness': within(text, source, value, lo, hi)}}
                   for key, value in fragments.items()]
        factors.append({'factor': 'anoxic_assay', 'level': {'kind': 'literal',
            'witness': within(text, source, 'were performed under strictly anoxic conditions.')}})
        return {'coverage': 'complete', 'factors': factors}

    def rate_selection(row, endpoint):
        cell = row['cells'][1]
        found = None
        for data_start, data in cell['data']:
            token = re.search(r'[0-9]+(?:\.[0-9]+)?', data)
            if token:
                value = token.group()
                position = raw_html.index(value, data_start, cell['end'])
                found = position, value
                break
        assert found is not None
        position, value = found
        w = witness(raw_html, source, cell['start'], cell['end'], 'original')
        return {'value': {'witness': w, 'number_start': position - cell['start'],
                         'number_end': position - cell['start'] + len(value)},
            'unit': unit(endpoint), 'spread': {'kind': 'unreported', 'magnitude': None, 'unit': None, 'witnesses': []}}

    result = {}
    for endpoint in ('nadh', 'h2'):
        for partner, omitted_label in (('Fd', 'Hyd'), ('Hyd', 'Fd')):
            reference, omitted = rows[endpoint, 'Fd + Hyd'], rows[endpoint, omitted_label]
            arms = {}
            for role, row in (('reference', reference), ('omitted', omitted)):
                arms[role] = {'subject': subject, 'partner': partners[partner], 'endpoint': endpoints[endpoint],
                    'normalization': normalization, 'partner_state': 'present' if role == 'reference' else 'absent',
                    'conditions': conditions(endpoint, partner),
                    'measurement_identity': witness(raw_html, source, row['start'], row['end'], 'original'),
                    'origin': 'reported', 'rate': rate_selection(row, endpoint)}
            arms['addback'] = None
            literals = dict.fromkeys(('subject','partner','experiment','endpoint','normalization',
                'reference_condition','omitted_condition','addback_condition','function'))
            literals.update(subject=subject, partner=partners[partner], experiment=heading,
                endpoint=endpoints[endpoint], normalization=normalization)
            result[endpoint + '_' + partner] = {'source_ref': source, 'data_source_ref': source,
                'source_kind': 'primary_source', 'input_mode': 'native_source_spans',
                'literals': literals, 'interpretation_witnesses': [heading, *qualifications], 'arms': arms}
    return result, subject


def check_science(payloads):
    oracle = {'nadh_Fd': (Fraction(7), Fraction(1,10)), 'nadh_Hyd': (Fraction(7), Fraction(4)),
              'h2_Hyd': (Fraction(5), Fraction(1,50))}
    for name, (reference, omitted) in oracle.items():
        cells = payloads[name]['sheet']['cells']
        assert cells['reference_rate']['value'] == float(reference * 1000000)
        assert cells['omitted_rate']['value'] == float(omitted * 1000000)
        assert cells['partner_loss']['value'] == float((reference - omitted) * 1000000)
        assert math.isclose(cells['partner_loss_fraction']['value'], float((reference - omitted)/reference), rel_tol=1e-15)
    bounded = payloads['h2_Fd']['sheet']['cells']
    assert bounded['omitted_rate']['value'] is None and bounded['omitted_rate']['upper'] == 10000
    assert bounded['partner_loss']['value'] is None and bounded['partner_loss']['lower'] == 4990000
    assert Fraction(bounded['partner_loss_fraction']['lower']) <= Fraction(499,500)
    assert bounded['partner_loss_fraction']['upper'] == 1
    assert payloads['h2_Fd']['extraction']['native_evidence']['omitted']['rate']['value']['relation'] == 'lt'
    for payload in payloads.values():
        assert payload['extraction']['calculation']['comparison_checks']['reference_omitted']['status'] == 'matched'
        for name in ('addback_rate','addback_gain','addback_fraction','restored_reference_fraction'):
            assert payload['sheet']['cells'][name]['value'] is None
    for endpoint in ('nadh','h2'):
        a,b=(payloads[endpoint+'_'+partner]['extraction']['recipe']['inputs']['arms']['reference']['measurement']['measurement_id'] for partner in ('Fd','Hyd'))
        assert a == b


async def main():
    destination = HERE / 'primary_001'
    destination.mkdir(exist_ok=False)
    raw_path = ROOT / 'research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary_access_0.bin'
    raw = raw_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '318ac6fe96b509815001892dcaa996688c703175c7dedf88b663d99fe9c90bcf'
    text_path = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_configured_return_scientific_review_155/ROOT_PRIMARY_TEXT_001.txt'
    text = text_path.read_text()
    manifest = destination / 'source_only_input_manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []})+'\n')
    captured = {}
    with Store(destination / 'state') as store:
        store.create_problem(manifest_path=manifest)
        assert not store.targets()
        original = store.artifact(raw, 'text/html')
        derivative = store.artifact(text.encode(), 'text/plain')
        source = store.put('source', {'provider':'caller_retained_primary','accession':'PMC2223550',
            'uri':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/', 'artifact_ref':original,
            'text_ref':derivative,'request_ref':None,'version':None,'retrieved_at':None,'parent_source_refs':[]}, origin='caller')['id']
        arguments, subject = selectors(raw.decode(), text, source)
        (destination / 'root_selected_arguments.json').write_text(json.dumps(arguments,indent=2)+'\n')
        scope=store.validate_scope()
        assignment={'version':'literature_assignment_v1','source_refs':[source],'question_context_refs':[],
            'requested_partner_components':list(COMPONENTS)}
        schema=obj({'partner_cells':partner_cells_schema()})
        question='Evaluate the source-reported component omission effects for the purified complex, preserving actual measured endpoints, reported protocol factors, coupled-reporter limits and shared measurements. Return the requested numerical partner components without target correspondence or annotation credit.'
        commission={'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
            'goal':question,'scope':scope,'purpose':question,'schema_json':json.dumps(schema),'initial_report_json':'{}'},'report_update':{}}
        actions=[{'selection':{'kind':'tool','tool':'literature.partner.source.populate','arguments':argument},'report_update':{}}
                 for argument in arguments.values()]
        def receive(inputs):
            form,=inputs['child_reports']
            assert len(form['partner_cells']) == 32
            captured['form']=deepcopy(form)
            captured['received_refs']=inputs['literature_received_fact_display']['received_refs']
            commit={key:[] for key in store.reasoning_schema()['required']}
            anchor={key:value for key,value in subject.items() if key!='representation'}
            anchor['artifact_ref']=derivative
            commit['source_subjects']=[{'alias':'studied_complex','reference_type':'assay','source_ref':source,
                'label':subject['quote'],'anchor':anchor}]
            return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        summary=await run_workflow(store,ToolRegistry(store),provider=ScriptedProvider([commission,*actions,receive]),
            run_dir=destination/'run',controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 else 4),
            project_credit=scorer,initial_known_record_refs=[source],
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=[source]),),
            binding_definitions={'credit':scorer.as_record()})
        assert summary['credit']==0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==6
        assert not store.list('assessment') and not store.list('observation')
        attempt=store.db.execute('SELECT * FROM runtime_report_attempts WHERE failure IS NULL').fetchone()
        assert json.loads(attempt['form'])==captured['form']
        run_id=attempt['run_id']
        repository=LiteraturePartnerRepository(store,run_id)
        operations=[json.loads(row['outcome']) for row in store.db.execute('SELECT outcome FROM literature_partner_operations ORDER BY rowid')]
        payloads={name:repository.read(outcome['result']['sheet_ref']) for name,outcome in zip(arguments,operations,strict=True)}
        check_science(payloads)
        parent=BindingContext(run_id,attempt['parent_episode_id'],'annotation',(('annotation','root'),),scope,{}, {},tuple(captured['received_refs']))
        descriptor=LiteratureEpisodes(None,rate_population=True,reference_parent_sources=[source]).as_record()
        saved_artifacts={store.get(outcome['result']['sheet_ref'])[field] for outcome in operations for field in ('artifact_ref','request_ref')}
        (destination/'typed_return.json').write_text(json.dumps(captured['form'],indent=2)+'\n')
        (destination/'populated_sheets.json').write_text(json.dumps(payloads,indent=2)+'\n')
        (destination/'saved_binding.json').write_text(json.dumps(descriptor,indent=2)+'\n')
    with Store(destination/'state') as store:
        get=store.get_artifact
        def retained_only(reference):
            assert reference in saved_artifacts,'saved reconstruction accessed scientific source bytes'
            return get(reference)
        def forbidden(*args,**kwargs):
            raise AssertionError('saved reconstruction repeated source reading or scientific calculation')
        store.get_artifact=retained_only
        import gene_annotation_episode.literature_partner_storage as storage
        import gene_annotation_episode.literature_partner_native_inputs as native
        import gene_annotation_episode.literature_partner_calculations as calculator
        storage.read_partner_inputs=forbidden
        native.read_partner_native_inputs=forbidden
        calculator.populate_partner_components=forbidden
        from gene_annotation_episode.literature_assay_inputs import _Sources
        _Sources.source=forbidden
        _Sources.witness=forbidden
        store.db.execute('PRAGMA query_only=ON')
        changes=store.db.total_changes
        services=WorkflowServices(SimpleNamespace(store=store,run_id=run_id,tools=ToolRegistry(store)))
        binding,=compose_episode_bindings(services,store=store,journal=Journal(store,run_id),execution_backend=None,
            descriptors=[descriptor],job_episodes=None,resource_estimator=None,role_credit_bindings={}).bindings
        assert binding.received_report_facts(parent)['literature_partner_cells']==captured['form']['partner_cells']
        assert store.db.total_changes==changes
    imports={name:str(Path(module.__file__).resolve()) for name,module in list(sys.modules.items())
        if name.startswith(('gene_annotation_episode','method_loop','test_')) and getattr(module,'__file__',None)}
    assert all(Path(path).is_relative_to(PIN) for path in imports.values())
    result={'scope':'Root-reviewed original-source selections and controlled episode decisions; no configured-model scientific success or A105 adequacy claim',
        'source_sha256':hashlib.sha256(raw).hexdigest(),'source_only_targets':0,'source_derivative_sha256':hashlib.sha256(text.encode()).hexdigest(),
        'case_names':list(arguments),'selected_population_operations':4,'original_typed_rows':32,'runtime_observations':6,
        'independent_preparation_count':None,'statistical_uncertainty':'not_evaluated','annotation_credit':0,
        'shared_reference_measurements':'one within each endpoint reused across its two contrasts; not independent replication',
        'censoring_limit':'strict lt retained in saved native evidence; existing partner numeric return uses conservative closed nonnegative enclosures',
        'cold_reconstruction':'exact original admitted rows; original/derivative scientific bytes and readers/calculator blocked before factory; query_only',
        'imports':imports}
    (destination/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='imports'},indent=2))


if __name__=='__main__':
    asyncio.run(main())
