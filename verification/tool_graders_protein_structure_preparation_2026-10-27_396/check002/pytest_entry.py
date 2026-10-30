import json, pathlib, runpy, sys
root = pathlib.Path(__file__).resolve().parent
try:
    runpy.run_module('pytest', run_name='__main__')
finally:
    imports = {name: str(getattr(module, '__file__', '')) for name, module in sys.modules.copy().items() if name.startswith(('gene_annotation_episode', 'method_loop'))}
    (root / 'executed_imports.json').write_text(json.dumps(imports, indent=2))
    assert all(pathlib.Path(path).is_relative_to(root / 'source_snapshot') for path in imports.values() if path)
