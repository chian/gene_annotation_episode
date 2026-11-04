"""The actual callable map and a deliberately simple test retriever.

The caller supplies real registry contracts. Retrieval selects names from that
map; it never manufactures operations or installs a tool implementation.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import errno
import hashlib
import json
from pathlib import Path
import re
import tempfile

from jsonschema import Draft202012Validator
from method_loop.durable import canonical, content_digest


VERSION = "scientific_tool_library_v1"


def tool_names(value):
    if (not isinstance(value, list) or any(not isinstance(name, str) or not name.strip()
            for name in value) or len(value) != len(set(value))):
        raise ValueError("scientific_selected_tools_invalid")
    return list(value)


def _catalog(value):
    if isinstance(value, Mapping):
        if any(not isinstance(entry, Mapping) or "name" in entry and entry["name"] != name
                for name, entry in value.items()):
            raise ValueError("scientific_tool_catalog_invalid")
        value = [{"name": name, **entry} for name, entry in value.items()]
    if not isinstance(value, (list, tuple)):
        raise ValueError("scientific_tool_catalog_invalid")
    entries = json.loads(canonical(value))
    names = tool_names([entry.get("name") if isinstance(entry, dict) else None for entry in entries])
    for entry in entries:
        if not isinstance(entry.get("input_schema"), dict):
            raise ValueError("scientific_tool_catalog_invalid")
        Draft202012Validator.check_schema(entry["input_schema"])
        if "description" in entry and not isinstance(entry["description"], str):
            raise ValueError("scientific_tool_catalog_invalid")
    return {name: entry for name, entry in sorted(zip(names, entries))}


def catalog(*, retrieval_mode=None):
    method = ("A single configured FAST call selects relevant names from the complete real map. "
        if retrieval_mode == "semantic_fast_v1" else
        "This explicit literal test retriever matches words in real tool names and descriptions. ")
    return [{"name": "process.tools", "description":
        "Retrieve zero or more actual callable tools relevant to the desired child investigation. "
        + method + "Copy result.tools "
        "directly into the child's selection.tools slot. Results include original callable contracts; "
        "retrieval runs no scientific operation and selects no child.",
        "input_schema": {"type": "object", "properties": {
            "investigation": {"type": "string", "minLength": 1}},
            "required": ["investigation"], "additionalProperties": False}}]


class ScientificToolLibrary:
    @classmethod
    def freeze(cls, directory, *, catalog):
        directory = Path(directory)
        if (directory / "index.json").is_file():
            existing = cls(directory)
            if existing.catalog() != list(_catalog(catalog).values()):
                raise ValueError("scientific_tool_catalog_changed")
            return existing
        if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
            raise ValueError("scientific_tool_snapshot_invalid")
        content = {"version": VERSION, "tools": list(_catalog(catalog).values())}
        value = {**content, "catalog_sha256": content_digest(content)}
        directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".scientific-tools-", dir=directory.parent) as temporary:
            staging = Path(temporary)
            (staging / "index.json").write_text(canonical(value) + "\n", encoding="utf-8")
            try:
                staging.rename(directory)
            except OSError as error:
                if error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                    raise
                return cls.freeze(directory, catalog=catalog)
        return cls(directory)

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        path = self.directory / "index.json"
        raw = path.read_bytes()
        value = json.loads(raw)
        if (set(value) != {"version", "tools", "catalog_sha256"}
                or value["version"] != VERSION
                or value["catalog_sha256"] != content_digest({
                    "version": VERSION, "tools": value["tools"]})
                or raw != (canonical(value) + "\n").encode("utf-8")):
            raise ValueError("scientific_tool_snapshot_changed")
        self._tools = _catalog(value["tools"])
        self._file_sha256 = hashlib.sha256(raw).hexdigest()
        self._record = {"version": VERSION, "catalog_sha256": value["catalog_sha256"]}

    def _check(self):
        path = self.directory / "index.json"
        if (not path.resolve().is_relative_to(self.directory)
                or hashlib.sha256(path.read_bytes()).hexdigest() != self._file_sha256):
            raise ValueError("scientific_tool_snapshot_changed")

    def as_record(self):
        self._check()
        return deepcopy(self._record)

    def catalog(self):
        self._check()
        return deepcopy(list(self._tools.values()))

    def resolve(self, names, available_catalog=None):
        self._check()
        names = tool_names(names)
        available = None if available_catalog is None else _catalog(available_catalog)
        result = []
        for name in names:
            if name not in self._tools:
                raise ValueError("scientific_tool_unknown:" + name)
            if available is not None and available.get(name) != self._tools[name]:
                raise ValueError("scientific_tool_contract_changed:" + name)
            result.append(deepcopy(self._tools[name]))
        return result

    def retrieve_literal_test(self, investigation):
        """Test retrieval: any non-stopword shared with a real name/description.

        There is no semantic relevance or completeness guarantee and no quota.
        """
        if not isinstance(investigation, str) or not investigation.strip():
            raise ValueError("scientific_tool_investigation_invalid")
        # This is an explicit test retrieval algorithm, not a biological
        # suitability claim. There are no bundles, fabricated synonyms or quota.
        ignored = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
            "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "with"}
        terms = set(re.findall(r"[a-z0-9]+", investigation.casefold())) - ignored
        selected = []
        for entry in self.catalog():
            words = set(re.findall(r"[a-z0-9]+", (entry["name"] + " " +
                entry.get("description", "")).casefold()))
            if terms & words:
                selected.append(entry["name"])
        return {"investigation": investigation, "tools": selected,
            "catalog": self.resolve(selected)}

    def retrieve(self, investigation):
        """Compatibility name for the original, explicitly literal test mode."""
        return self.retrieve_literal_test(investigation)


__all__ = ["ScientificToolLibrary", "catalog", "tool_names"]
