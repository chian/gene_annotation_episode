import json, os, pathlib, runpy, sys
root = pathlib.Path(__file__).resolve().parent
os.environ.update({k: str(root / 'temporary') for k in ('TMPDIR', 'TMP', 'TEMP')})
import gene_annotation_episode.episode_services as service
assert pathlib.Path(service.__file__).is_relative_to(root / 'source_snapshot')
(root / 'executed_imports_before.json').write_text(json.dumps({'service': service.__file__}, indent=2))
try:
    runpy.run_module('pytest', run_name='__main__')
finally:
    imports = {name: str(getattr(module, '__file__', '')) for name, module in sys.modules.copy().items() if name.startswith(('gene_annotation_episode', 'method_loop'))}
    (root / 'executed_imports_after.json').write_text(json.dumps(imports, indent=2))
    assert all(pathlib.Path(path).is_relative_to(root / 'source_snapshot') for path in imports.values() if path)
