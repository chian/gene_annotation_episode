"""A104 private source closure for the selected evolutionary worker."""
import ast
from pathlib import Path
from .a104_native_controls import require

_PACKAGES = {"jsonschema": "jsonschema", "attrs": "attr", "referencing": "referencing", "rpds-py": "rpds",
    "jsonschema-specifications": "jsonschema_specifications"}
_OPTIONAL = {"typing-extensions": "typing_extensions", "idna": "idna", "jsonpointer": "jsonpointer", "fqdn": "fqdn",
    "rfc3987": "rfc3987", "rfc3986-validator": "rfc3986_validator", "rfc3987-syntax": "rfc3987_syntax",
    "rfc3339-validator": "rfc3339_validator", "webcolors": "webcolors", "uri-template": "uri_template",
    "isoduration": "isoduration", "lark": "lark", "arrow": "arrow", "python-dateutil": "dateutil", "six": "six"}


def _source_closure(module_root, modules):
    root, paths, pending = Path(module_root), {}, list(modules) + ["gene_annotation_episode.episodic_workflow.root.a104.__init__"]
    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = root / (name.replace(".", "/") + ".py")
        if not path.is_file() and (root / name.replace(".", "/") / "__init__.py").is_file():
            name += ".__init__"
            path = root / (name.replace(".", "/") + ".py")
        require(path.is_file(), "native_dependency_unavailable")
        paths[name] = path
        package = name.rsplit(".", 1)[0]
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")[:len(package.split(".")) - node.level + 1]
                    imported = ".".join([*base, *([node.module] if node.module else [])])
                else:
                    imported = node.module or ""
                if node.module is None and (imported == "gene_annotation_episode" or imported.startswith("gene_annotation_episode.")):
                    pending.extend(imported + "." + alias.name for alias in node.names)
                elif imported.startswith("gene_annotation_episode."):
                    pending.append(imported)
            elif isinstance(node, ast.Import):
                pending.extend(a.name for a in node.names if a.name.startswith("gene_annotation_episode."))
    return paths


