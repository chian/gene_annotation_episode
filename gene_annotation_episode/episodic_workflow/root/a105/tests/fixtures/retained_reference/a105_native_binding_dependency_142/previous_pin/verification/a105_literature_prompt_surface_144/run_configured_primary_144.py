"""Fresh source-evidence caller; preparation performs no scientific extraction.

The source file is caller selected, retained as exact bytes and initially
received by the reference-evidence parent. No measurements, span selectors,
interpretations or model answers are prepopulated. The caller supplies the
scientific assignment through --question. Execution uses the ordinary configured
ModelConnection, controller and LiteratureEpisodes with the existing pending
contract-information profile. This script owns no iterative decision loop.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.providers import default_config_path
from gene_annotation_episode.public_configuration import configured_tools
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools


def prepare(directory: Path, *, source: Path, source_sha256: str, question: str, media_type: str = 'text/html'):
    """Bind exact caller source custody, without parsing experimental operands."""
    directory, source = directory.resolve(), source.resolve()
    raw = source.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != source_sha256:
        raise ValueError('caller_selected_source_digest_mismatch')
    if not question.strip():
        raise ValueError('substantive_caller_scientific_question_required')
    directory.mkdir(parents=True, exist_ok=False)
    manifest = directory/'source_only_input_manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []})+'\n')
    store = Store(directory/'state')
    try:
        # A source-only reference investigation has no invented target sequence.
        # Empty original subject scope is permitted by existing scope validation.
        store.create_problem(manifest_path=manifest)
        artifact = store.artifact(raw, media_type)
        supplied = store.put('source', {'provider': 'caller_retained_primary',
            'accession': None, 'uri': source.as_uri(), 'artifact_ref': artifact,
            'text_ref': None, 'request_ref': None, 'version': None,
            'retrieved_at': None}, origin='caller')['id']
        descriptor = LiteratureEpisodes.reference_evidence(None, source_refs=[supplied]).as_record()
        configuration = tomllib.loads(default_config_path().read_text())
        tool_configuration = configured_tools({key: configuration[key] for key in (
            'public', 'local_tools', 'local_jobs', 'knowledge_library_directory',
            'history', 'resource_id') if key in configuration})
        record = {'version': 'literature_source_caller_144_v2',
            'source_path': str(source), 'source_sha256': actual, 'source_media_type': media_type,
            'source_ref': supplied, 'artifact_ref': artifact,
            'scope': store.validate_scope(), 'scientific_question': question,
            'scientific_scope': 'Reference experimental evidence only; target correspondence and annotation credit remain separate.',
            'received_source_meaning': 'Caller-supplied exact original bytes; no extracted measurements or interpretations inherited.',
            'episode_binding_descriptor': descriptor,
            'decision_protocol': 'decision_exchange_v1',
            'configuration': configuration, 'tool_configuration': tool_configuration}
        (directory/'prepared_caller.json').write_text(json.dumps(record, indent=2)+'\n')
        return record
    finally:
        store.close()


def assignment_text(prepared: dict):
    """Supply caller reference-only boundaries in the actual recurring TASK."""
    return (prepared['scientific_question'] + '\n\nScope and interpretation constraints:\n'
        + prepared['scientific_scope'] + '\nNo annotation target sequence was supplied. '
        'Begin with the assigned source contents. Select your own reads, source locations, '
        'experimental relationships and numerical operands from evidence actually obtained. '
        'Preserve coupled-readout and control limitations; do not assume an observed '
        'preparation signal isolates the reference molecule or establishes a named product.')


async def execute(directory: Path, prepared: dict):
    """Start one ordinary Workflow; its configured controller owns continuation."""
    with Store(directory/'state') as store:
        tools = build_tools(store, prepared['tool_configuration'])
        try:
            return await run_workflow(store, tools, run_dir=directory/'run',
                goal=assignment_text(prepared),
                initial_known_record_refs=[prepared['source_ref']],
                episode_binding_descriptors=[prepared['episode_binding_descriptor']],
                provider_config=prepared['configuration'],
                annotation_child_roles=('literature',),
                decision_protocol=prepared['decision_protocol'])
        except Exception as error:
            diagnostic = {'exception_type': type(error).__name__, 'message': str(error),
                'failure': getattr(error, 'failure', None)}
            (directory/'execution_failure.json').write_text(json.dumps(diagnostic, indent=2)+'\n')
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--media-type', default='text/html',
        help='Caller-declared original representation; the retained primary asset is HTML.')
    parser.add_argument('--question', required=True,
        help='Actual scoped scientific assignment supplied by the caller.')
    parser.add_argument('--execute', action='store_true',
        help='Start the configured workflow after retaining the supplied source.')
    args = parser.parse_args()
    prepared = prepare(args.run_dir, source=args.source,
        source_sha256=args.source_sha256, question=args.question, media_type=args.media_type)
    if args.execute:
        summary = asyncio.run(execute(args.run_dir.resolve(), prepared))
        (args.run_dir/'execution_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary, indent=2))
    else:
        print(json.dumps(prepared, indent=2))


if __name__ == '__main__':
    main()
