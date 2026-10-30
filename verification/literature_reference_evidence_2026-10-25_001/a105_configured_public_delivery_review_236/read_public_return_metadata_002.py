"""Count only admitted typed scientific-return fields; no provider payload access."""
from pathlib import Path
import json
import sqlite3
import time

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / 'a105_joined_control_binding_review_141/configured_primary_006'
RUN_ID = 'run_5ba00e92c4f441d69634b4761f2d6dc3'
db = sqlite3.connect((RUN / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
db.execute('BEGIN')
reports = []
for row in db.execute("SELECT parent_episode_id,child_episode_id,decision_index,"
        "json_extract(contract,'$.measurements.schema') AS declared_schema,form "
        "FROM runtime_report_attempts WHERE run_id=? AND form IS NOT NULL AND failure IS NULL "
        "ORDER BY decision_index", (RUN_ID,)):
    schema = json.loads(row['declared_schema']) if row['declared_schema'] else {}
    form = json.loads(row['form'])
    fields = []
    for name, node in schema.get('properties', {}).items():
        value = form.get(name)
        fields.append(dict(field=name, x_source=node.get('x-source'), stored_type=type(value).__name__,
            rows=len(value) if isinstance(value, list) else None,
            rows_with_numeric_value_or_conditional_value=sum(isinstance(item, dict)
                and any(type(item.get(key)) in (int, float) for key in ('value', 'conditional_value'))
                for item in value) if isinstance(value, list) else None))
    reports.append(dict(parent_episode_id=row['parent_episode_id'], child_episode_id=row['child_episode_id'],
                        decision_index=row['decision_index'], fields=fields))
assert db.total_changes == 0
db.close()
result = dict(observed_unix=time.time(), run_id=RUN_ID, admitted_scientific_reports=reports,
    readonly_changes=0,
    inspected='Only successful runtime_report_attempts.form and its original declared schema subfield; aggregate public typed scientific-return metadata.',
    excluded='No runtime_model_calls request/response, actual provider logs, prompts, conversations or private model payloads accessed.',
    count_meaning='Rows with a numeric top-level value/conditional_value only. These are dependent component rows, not independent experiments, graders, scientific truth or assay adequacy.',
    scientific_verification='Original-source meaning, covariance/dependence and numerical correctness of these actual-model returns remain to be independently assessed. No actual new228/231 binding success claim.')
with (HERE / 'PUBLIC_RETURN_METADATA_002.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(dict(successful_forms=len(reports),
    fields=[field for report in reports for field in report['fields']], readonly_changes=0), indent=2))
