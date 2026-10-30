"""Exercise the actual frozen instruction library for native paired BLAST."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

HERE = Path(__file__).parent / 'knowledge_check001'


def verify():
    from gene_annotation_episode.native_blast_contracts import PROGRAMS
    from gene_annotation_episode.tool_knowledge import ToolKnowledge

    library = ToolKnowledge.freeze(HERE / 'snapshot')
    entry = library.entry('native-blast-pairwise')['entry']
    assert set(entry['tool_names']) == {'native.' + name for name in PROGRAMS}
    assert entry['resource_kinds'] == ['local']
    assert all((ROOT / name).is_file() for name in entry['provenance'])
    for name in entry['tool_names']:
        assert 'native-blast-pairwise' in library.entries_for_tool(name)
    search = library.search(query='BLAST pairwise local', offset=0, limit=20)
    assert any(row['entry_id'] == 'native-blast-pairwise' for row in search['entries'])
    query = dict(entry_id='native-blast-pairwise', section_id='operation-results',
                 offset=0, limit=23)
    pages = []
    while query is not None:
        result = library.execute('knowledge.read', query)
        assert result['status'] == 'completed'
        assert result['record_refs'] == result['changed_record_refs'] == []
        pages.append(result['result']['text'])
        query = result['result']['next_query']
    text = ''.join(pages)
    assert text == (ROOT / 'gene_annotation_episode/knowledge/native-blast-pairwise.md').read_text()
    result = {'entry': entry, 'page_count': len(pages),
              'complete_instruction_bytes_recovered': True,
              'new_scientific_records': 0, 'native_execution': False}
    (HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'programs': len(entry['tool_names']), 'pages': len(pages),
                      'complete_instruction_bytes_recovered': True}))


if __name__ == '__main__':
    if sys.argv[1:] == ['worker']:
        verify()
    else:
        HERE.mkdir()
        outcome = run_local_job([sys.executable, str(Path(__file__).resolve()), 'worker'],
            cwd=HERE, policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None),
            env={'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1'})
        receipt = {'returncode': outcome.returncode, 'metadata': outcome.metadata,
                   'stdout_path': str(outcome.stdout_path), 'stderr_path': str(outcome.stderr_path)}
        (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))
        print(outcome.stdout_path.read_text())
        print(outcome.stderr_path.read_text())
        raise SystemExit(outcome.returncode)
