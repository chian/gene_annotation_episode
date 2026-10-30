import hashlib, importlib, json, pathlib, sys
candidate=pathlib.Path(sys.argv[1]).resolve()
sys.dont_write_bytecode=True
sys.path.insert(0,str(candidate))
result={}
for path in sorted((candidate/"gene_annotation_episode").glob("bvbrc*.py")):
    if "def implementation_sha256" not in path.read_text():
        continue
    module=importlib.import_module("gene_annotation_episode."+path.stem)
    result[path.name]={"pin":module.implementation_sha256(),
        "dependencies":{name:hashlib.sha256(path.with_name(name).read_bytes()).hexdigest() for name in sorted(module._DEPENDENCIES)}}
print(json.dumps(result,indent=2))
