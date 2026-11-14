"""Original explicit raw support-receipt read/admission protocols."""
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_custody import _references
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_records import PROVIDER
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_host import SUPPORT_SOURCE
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain


def standalone_received_support_refs(host, context):
    host.custody.authenticate(context, allow_unsaved=True)
    rows = host.store.db.execute('SELECT decision_index FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index', (host.run_id, context.episode_id)).fetchall()
    result = []
    for row in rows:
        _, form, schema = host.custody._attempt(context, row['decision_index'])
        for reference, namespace in _references(form, schema):
            if namespace not in {None, 'source', 'bvbrc_appservice_support'}:
                continue
            if host.store.get(reference).get('provider') != PROVIDER:
                continue
            record = host.records.read(reference)
            host.custody.possession(context, reference)
            if record['contract'] != 'TaskHandoff' and reference not in result:
                result.append(reference)
    return result

def standalone_validate_received_report(host, context, form, schema):
    names = [name for name, node in plain(schema).get('properties', {}).items() if node.get('x-source') == SUPPORT_SOURCE]
    if names:
        expected = host.facts(context)[SUPPORT_SOURCE] if host.owns_context(context) else host.received_support_refs(context)
        if any((canonical(form[name]) != canonical(expected) for name in names)):
            raise ValueError('appservice_received_support_refs_conflict')
