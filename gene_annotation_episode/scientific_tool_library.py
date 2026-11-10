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

from method_loop.durable import canonical, content_digest

from .tool_schema_validation import check_tool_schema


VERSION = "scientific_tool_library_v1"
INFO_VERSION = "scientific_tool_library_v2"


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
        check_tool_schema(entry["input_schema"])
        if "description" in entry and not isinstance(entry["description"], str):
            raise ValueError("scientific_tool_catalog_invalid")
    return {name: entry for name, entry in sorted(zip(names, entries))}


def _profiles(value, resource=None):
    from .tool_information import RESOURCE_KINDS, resource_kind
    if isinstance(value, Mapping):
        if any(not isinstance(entry, Mapping) or 'name' in entry and entry['name'] != name
               for name, entry in value.items()):
            raise ValueError('scientific_tool_catalog_invalid')
        value = [{'name': name, **entry} for name, entry in value.items()]
    if not isinstance(value, (list, tuple)):
        raise ValueError('scientific_tool_catalog_invalid')
    result = {}
    for supplied in value:
        entry = json.loads(canonical(supplied))
        if not isinstance(entry, dict) or not isinstance(entry.get('name'), str):
            raise ValueError('scientific_tool_catalog_invalid')
        kind = resource or entry.get('resources') or resource_kind(entry['name'])
        if resource is not None and entry.get('resources', resource) != resource:
            raise ValueError('scientific_tool_resource_conflict:' + entry['name'])
        if kind not in RESOURCE_KINDS:
            raise ValueError('scientific_tool_resource_kind_required:' + entry['name'])
        if not isinstance(entry.get('input_schema'), dict):
            raise ValueError('scientific_tool_catalog_invalid')
        if ('instructions' in entry and (not isinstance(entry['instructions'], str)
                or not entry['instructions'].strip())):
            raise ValueError('scientific_tool_instructions_required:' + entry['name'])
        check_tool_schema(entry['input_schema'])
        key = entry['name'], kind
        if key in result:
            raise ValueError('scientific_tool_resource_variant_duplicate')
        result[key] = entry
    return result


def _tool_information(catalog, resource_catalogs):
    from .tool_information import make_tool_info, tool_info_selection, workflow_execution_catalogs
    profiles = {}
    for kind, values in workflow_execution_catalogs().items():
        profiles.update(_profiles(values, kind))
    profiles.update(_profiles(catalog))
    for kind, values in (resource_catalogs or {}).items():
        profiles.update(_profiles(values, kind))
    ordered = sorted(profiles)
    information = []
    for key in ordered:
        profile = profiles[key]
        information.append(({'name': key[0], 'description': profile.get('description'),
            'resources': key[1], 'instructions': profile['instructions']}
            if 'instructions' in profile else make_tool_info(profile, key[1])))
        from .execution_guidance import recipe
        information[-1]['instructions'] += '\n\n' + recipe(*key)
    return (tool_info_selection(information),
            [{'name': key[0], 'resources': key[1], 'contract': profiles[key]} for key in ordered])


def catalog(*, retrieval_mode=None, tool_info=False):
    method = ("A single configured FAST call selects relevant names from the complete real map. "
        if retrieval_mode == "semantic_fast_v1" else
        "This explicit literal test retriever matches words in real tool names and descriptions. ")
    if tool_info:
        return [{"name": "process.tools", "description":
            "Retrieve actual operation information for the desired child investigation. "
            "Parent rows contain name, description and one API/local/HPC resource kind. "
            "Select by name plus resources; the host supplies matching frozen instructions and "
            "the actual invocation contract to the child. Never compose descriptions or instructions. "
            "This retrieval performs no scientific work or child launch.",
            "input_schema": {"type": "object", "properties": {
                "investigation": {"type": "string", "minLength": 1}},
                "required": ["investigation"], "additionalProperties": False}}]
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
    def freeze(cls, directory, *, catalog, tool_info=False, resource_catalogs=None):
        if type(tool_info) is not bool or resource_catalogs is not None and not isinstance(resource_catalogs, Mapping):
            raise ValueError('scientific_tool_info_configuration_invalid')
        directory = Path(directory)
        if (directory / "index.json").is_file():
            existing = cls(directory)
            if existing.catalog() != list(_catalog(catalog).values()):
                raise ValueError("scientific_tool_catalog_changed")
            if existing.supports_tool_info and resource_catalogs is not None:
                for kind, values in resource_catalogs.items():
                    for key, entry in _profiles(values, kind).items():
                        if (key not in existing._resource_contracts
                                or not existing._matches_information_contract(key, entry)):
                            raise ValueError('scientific_tool_catalog_changed')
            return existing
        if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
            raise ValueError("scientific_tool_snapshot_invalid")
        content = {"version": VERSION, "tools": list(_catalog(catalog).values())}
        if tool_info:
            information, contracts = _tool_information(content['tools'], resource_catalogs)
            content.update(version=INFO_VERSION, tool_info=information, resource_contracts=contracts)
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
                return cls.freeze(directory, catalog=catalog, tool_info=tool_info,
                                  resource_catalogs=resource_catalogs)
        return cls(directory)

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        path = self.directory / "index.json"
        raw = path.read_bytes()
        value = json.loads(raw)
        fields = ({'version', 'tools', 'tool_info', 'resource_contracts', 'catalog_sha256'}
                  if value.get('version') == INFO_VERSION else {'version', 'tools', 'catalog_sha256'})
        if (set(value) != fields or value['version'] not in {VERSION, INFO_VERSION}
                or value["catalog_sha256"] != content_digest({key: item for key, item in value.items()
                                                            if key != 'catalog_sha256'})
                or raw != (canonical(value) + "\n").encode("utf-8")):
            raise ValueError("scientific_tool_snapshot_changed")
        self._tools = _catalog(value["tools"])
        self.supports_tool_info = value['version'] == INFO_VERSION
        self._information, self._resource_contracts = {}, {}
        if self.supports_tool_info:
            from .tool_information import tool_info_selection
            rows = tool_info_selection(value['tool_info'])
            if any(set(row) != {'name', 'description', 'resources', 'instructions'} for row in rows):
                raise ValueError('scientific_tool_snapshot_changed')
            self._information = {(row['name'], row['resources']): row for row in rows}
            for entry in value['resource_contracts']:
                if set(entry) != {'name', 'resources', 'contract'}:
                    raise ValueError('scientific_tool_snapshot_changed')
                key = entry['name'], entry['resources']
                profile = _profiles([entry['contract']], entry['resources'])
                if key not in profile or key in self._resource_contracts:
                    raise ValueError('scientific_tool_snapshot_changed')
                self._resource_contracts[key] = profile[key]
            if set(self._information) != set(self._resource_contracts):
                raise ValueError('scientific_tool_snapshot_changed')
            for key, information in self._information.items():
                if information['description'] != self._resource_contracts[key].get('description'):
                    raise ValueError('scientific_tool_snapshot_changed')
            from .tool_information import comparable_contract
            for key, entry in _profiles(value['tools']).items():
                if (key not in self._resource_contracts or comparable_contract(entry)
                        != comparable_contract(self._resource_contracts[key])):
                    raise ValueError('scientific_tool_snapshot_changed')
        self._file_sha256 = hashlib.sha256(raw).hexdigest()
        self._record = {"version": value['version'], "catalog_sha256": value["catalog_sha256"]}

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

    def _require_tool_info(self):
        self._check()
        if not self.supports_tool_info:
            raise ValueError('scientific_tool_info_not_in_legacy_snapshot')

    def _matches_information_contract(self, key, entry):
        from .tool_information import comparable_contract
        return (comparable_contract(entry) == comparable_contract(self._resource_contracts[key])
            and ('instructions' not in entry
                 or entry['instructions'] == self._resource_contracts[key].get('instructions')
                 or entry['instructions'] == self._information[key]['instructions']))

    def parent_tool_info(self, available_catalog=None):
        self._require_tool_info()
        from .tool_information import parent_view
        keys = list(self._information)
        if available_catalog is not None:
            available = _profiles(available_catalog)
            keys = [key for key in keys if key in available]
            for key in keys:
                if not self._matches_information_contract(key, available[key]):
                    raise ValueError('scientific_tool_contract_changed:' + key[0])
        return parent_view([self._information[key] for key in keys])

    def resolve_tool_info(self, selection, available_catalog=None):
        self._require_tool_info()
        from .tool_information import tool_info_selection
        supplied = tool_info_selection(selection)
        available = None if available_catalog is None else _profiles(available_catalog)
        result = []
        for row in supplied:
            key = row['name'], row['resources']
            if key not in self._information:
                raise ValueError('scientific_tool_unknown:' + row['name'] + ':' + row['resources'])
            expected = self._information[key]
            if len(row) == 4 and row != expected:
                raise ValueError('scientific_tool_info_changed:' + row['name'])
            if available is not None and (key not in available or
                    not self._matches_information_contract(key, available[key])):
                raise ValueError('scientific_tool_contract_changed:' + row['name'] + ':' + row['resources'])
            result.append(deepcopy(expected))
        return result

    def resolve_invocations(self, selection, available_catalog=None):
        information = self.resolve_tool_info(selection, available_catalog)
        available = None if available_catalog is None else _profiles(available_catalog)
        return [{**deepcopy(self._resource_contracts[(row['name'], row['resources'])]
                            if available is None else available[(row['name'], row['resources'])]),
                 'resources': row['resources'], 'instructions': row['instructions']}
                for row in information]

    def retrieve_literal_test(self, investigation, available_catalog=None):
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
        if self.supports_tool_info:
            rows = [row for row in self.parent_tool_info(available_catalog) if terms & set(re.findall(
                r'[a-z0-9]+', (row['name'] + ' ' + row['description']).casefold()))]
            return {'investigation': investigation, 'child_tool_info': rows}
        selected = []
        for entry in self.catalog():
            words = set(re.findall(r"[a-z0-9]+", (entry["name"] + " " +
                entry.get("description", "")).casefold()))
            if terms & words:
                selected.append(entry["name"])
        return {"investigation": investigation, "tools": selected,
            "catalog": self.resolve(selected)}

    def retrieve(self, investigation, available_catalog=None):
        """Compatibility name for the original, explicitly literal test mode."""
        return self.retrieve_literal_test(investigation, available_catalog=available_catalog)


__all__ = ["ScientificToolLibrary", "catalog", "tool_names", "VERSION", "INFO_VERSION"]
