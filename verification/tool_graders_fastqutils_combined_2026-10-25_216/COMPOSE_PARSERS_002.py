"""Handle aligned optional-schema branches; retain the failed001 composition."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('composition001', HERE / 'COMPOSE_PARSERS_001.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
original_merge = m.merge_schema


def merge_schema(base, left, right, path=''):
    # These arrays contain corresponding structural branches, not value enums.
    # The existing recursive merge still rejects conflicting scalar semantics.
    if (path.endswith(('/anyOf', '/oneOf', '/allOf')) and
            all(type(v) is list for v in (base, left, right)) and
            len(base) == len(left) == len(right) and left != base and right != base):
        return [merge_schema(b, l, r, path + '/' + str(i))
                for i, (b, l, r) in enumerate(zip(base, left, right))]
    return original_merge(base, left, right, path)


if __name__ == '__main__':
    failure = HERE / 'PARSER_COMPOSITION_ATTEMPT_001.json'
    if not failure.exists():
        m.write_json(failure, dict(
            passed=False, exit_code=1, code='schema_composition_conflict',
            path='/$defs/Population/properties/section_key/anyOf',
            script_sha256=m.sha((HERE / 'COMPOSE_PARSERS_001.py').read_bytes()),
            partial_candidate='candidate', tests_executed=False,
            production_changed=False,
            explanation='Initial merge did not traverse corresponding optional branches; no schema result was published.'))
    m.merge_schema = merge_schema
    m.OUT = HERE / 'candidate_002'
    m.main()
