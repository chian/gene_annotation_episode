"""Original standalone AppService report/read protocols; explicit private ports select owned invocation."""
from ..communication import plain
from ..execution_contracts import digest
from ..bvbrc_appservice_host import SUPPORT_SOURCE

def standalone_appservice_facts(host, context):
    rows = host._own_receipts(context)
    schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
    facts = {'execution_handoff_refs': [r['source_ref'] for r in rows if r['contract'] == 'TaskHandoff'], SUPPORT_SOURCE: [r['source_ref'] for r in rows if r['contract'] != 'TaskHandoff'], 'execution_result_refs': host.publications.own_results(context), 'execution_completed': host.completion(context) is not None}
    for returns in (host.api.application_returns,):
        supplied = returns.facts(context, schema)
        if set(facts).intersection(supplied):
            raise ValueError('appservice_own_fact_source_conflict')
        facts.update(supplied)
    return facts

def standalone_appservice_completion(host, context):
    if context.role == 'results':
        return host.publications.completion(context)
    if context.role != 'launch_api':
        return None
    for record in reversed(host._own_receipts(context)):
        if record['contract'] != 'TaskHandoff':
            continue
        common = record['value']['receipt']
        host.read_handoff(record['source_ref'], context.scope)
        return {'version': 'practical_completion_v1', 'run_id': host.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'usable_handoff', 'operation_key': common['origin']['operation_key'], 'receipt_sha256': digest(common), 'validation_keys': ['usable_handoff']}
    return None

def standalone_publication_completion(publication, context):
    selected = plain(context.assignment).get('selector', {}).get('adapter')
    if selected is not None and (selected['adapter_id'], selected['adapter_version']) in {('bvbrc_tnseq', '1'), ('bvbrc_rnaseq', '1')}:
        publication.host.custody.authenticate(context, allow_unsaved=True)
        for _, outcome in reversed(list(publication.api._own_outcomes(context))):
            result = outcome.get('result') or {}
            if result.get('publication_ref') is None:
                continue
            refs = result.get('result_record_refs', [])
            if not refs:
                return None
            return publication.read(refs[-1], context.scope, episode_id=context.episode_id)['publication']['completion_proof']
        return None
    for reference in reversed(publication.own_results(context)):
        proof = publication.read(reference, context.scope, episode_id=context.episode_id)['publication']['completion_proof']
        if proof is not None:
            return proof
    return None
