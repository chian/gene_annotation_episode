from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import sys
import urllib.request

packet = Path(os.environ["RNA_PRODUCER_PACKET"])
sys.path.insert(0, str(packet / "native-site"))
import RNA
md = RNA.md()
settings = {}
for name in dir(md):
    if name.startswith("_") or name == "thisown":
        continue
    value = getattr(md, name)
    if callable(value):
        continue
    settings[name] = {"type": type(value).__name__, "value": value if type(value) in (int, float, str, bool) else None}
record = {"python_executable": sys.executable, "python_version": sys.version,
    "RNA_version": RNA.__version__, "distribution_version": importlib.metadata.version("ViennaRNA"),
    "module_path": RNA.__file__, "module_sha256": hashlib.sha256(Path(RNA.__file__).read_bytes()).hexdigest(),
    "extension_path": RNA._RNA.__file__, "extension_sha256": hashlib.sha256(Path(RNA._RNA.__file__).read_bytes()).hexdigest(),
    "INF": RNA.INF, "settings": settings,
    "params_load_doc": RNA.params_load.__doc__, "params_save_doc": RNA.params_save.__doc__,
    "turner_doc": RNA.params_load_RNA_Turner2004.__doc__,
    "mfe_doc": RNA.fold_compound.mfe.__doc__, "eval_doc": RNA.fold_compound.eval_structure.__doc__}
Path("probe.json").write_text(json.dumps(record, indent=2) + "\n")
relative = "src/ViennaRNA/eval/eval_structures.c"
raw = urllib.request.urlopen("https://raw.githubusercontent.com/ViennaRNA/ViennaRNA/v2.7.0/" + relative).read()
destination = packet / "primary-source" / relative
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_bytes(raw)
print(json.dumps(record, indent=2))
