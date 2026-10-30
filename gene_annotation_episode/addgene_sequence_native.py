"""Pure readers for supplied Addgene sequence-page representations.

Page categories and sequence identifiers are source assertions.  This module
does not acquire a page, follow a locator, infer topology, or assign confidence.
Raw response bytes and transport provenance remain the caller's responsibility.
"""
from __future__ import annotations

from copy import deepcopy
from html import unescape
from html.parser import HTMLParser
import re


_CATEGORIES = {
    "addgene-full": ("full", "addgene_verified"),
    "addgene-partial": ("partial", "addgene_verified"),
    "depositor-full": ("full", "depositor"),
    "depositor-partial": ("partial", "depositor"),
}
_ISSUES = (
    "authentication_required", "response_incomplete", "representation_unavailable",
    "invalid_encoding", "invalid_html", "empty_literal", "invalid_literal",
    "incomplete_literal", "ambiguous_sequence_identity", "conflicting_sequence_literals",
    "download_required",
)
_DNA = frozenset("ACGTRYSWKMBDHVNacgtryswkmbdhvn")
_ASCII_SPACE = " \t\r\n\v\f"
_LINK = re.compile(r"(?:https://(?:www\.)?addgene\.org)?/browse/sequence/([0-9]+)/?(?:[?#].*)?\Z")
_ID = re.compile(r"(?:sequence[-_])([0-9]+)\Z")
_VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _nullable(kind, **extra):
    return {"type": [kind, "null"], **extra}


_LOCATOR_SCHEMA = _object({
    "tag": {"type": "string", "minLength": 1},
    "attribute": {"type": "string", "minLength": 1},
    "value": {"type": "string", "minLength": 1},
    "source_element_ordinal": {"type": "integer", "minimum": 0},
})
_ROW_SCHEMA = _object({
    "record_ordinal": {"type": "integer", "minimum": 0},
    "sequence_id": _nullable("string", pattern=r"^[0-9]+$"),
    "source_completeness": {"enum": ["full", "partial", "unknown"]},
    "source_verification": {"enum": ["addgene_verified", "depositor", "unknown"]},
    "section_id": _nullable("string"),
    "native_header": _nullable("string"),
    "sequence": _nullable("string", minLength=1),
    "sequence_status": {"enum": ["available", "authentication_required", "download_required", "invalid", "unavailable"]},
    "locators": {"type": "array", "minItems": 1, "items": _LOCATOR_SCHEMA},
    "native_sequence_text": _nullable("string"),
    "issue_codes": {"type": "array", "uniqueItems": True, "items": {"enum": list(_ISSUES)}},
})
ADDGENE_SEQUENCE_PAGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    **_object({
        "version": {"const": "addgene_sequence_page_v1"},
        "source_ref": {"type": "string", "minLength": 1},
        "requested_id": {"type": "string", "pattern": r"^[0-9]+$"},
        "response_complete": {"type": "boolean"},
        "parse_status": {"enum": ["complete", "partial", "invalid"]},
        "authentication_required": {"type": "boolean"},
        "records": {"type": "array", "items": _ROW_SCHEMA},
        "issues": {"type": "array", "uniqueItems": True, "items": _object({
            "code": {"enum": list(_ISSUES)},
            "record_ordinal": _nullable("integer", minimum=0),
        })},
    }),
}


def _schema_check(value, schema):
    """Validate this closed JSON schema without importing an execution library."""
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise ValueError("addgene_sequence_schema")
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        raise ValueError("addgene_sequence_schema")
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    wanted = schema.get("type")
    if wanted is not None:
        wanted = [wanted] if type(wanted) is str else wanted
        if type(value) not in [types[item] for item in wanted]:
            raise ValueError("addgene_sequence_schema")
    if value is None:
        return
    if type(value) is dict:
        if set(value) != set(schema["properties"]):
            raise ValueError("addgene_sequence_schema")
        for key, item in value.items():
            _schema_check(item, schema["properties"][key])
    elif type(value) is list:
        if len(value) < schema.get("minItems", 0):
            raise ValueError("addgene_sequence_schema")
        if schema.get("uniqueItems") and any(item in value[:index] for index, item in enumerate(value)):
            raise ValueError("addgene_sequence_schema")
        for item in value:
            _schema_check(item, schema["items"])
    elif type(value) is str:
        if len(value) < schema.get("minLength", 0) or ("pattern" in schema and re.fullmatch(schema["pattern"], value) is None):
            raise ValueError("addgene_sequence_schema")
    elif type(value) is int and value < schema.get("minimum", value):
        raise ValueError("addgene_sequence_schema")


def _literal(text):
    lines = re.split(r"\r\n|\r|\n", text)
    first = next((index for index, line in enumerate(lines) if line.strip(_ASCII_SPACE)), None)
    if first is None:
        return None, None, "empty_literal"
    header = lines[first] if lines[first].startswith(">") else None
    body = lines[first + 1:] if header is not None else lines[first:]
    sequence = "".join(body).translate({ord(symbol): None for symbol in _ASCII_SPACE})
    if not sequence:
        return header, None, "empty_literal"
    if not set(sequence) <= _DNA or header is not None and not header[1:].strip(_ASCII_SPACE):
        return header, None, "invalid_literal"
    return header, sequence, None


def _page_status(page):
    if any(issue["code"] in {"invalid_encoding", "invalid_html"} for issue in page["issues"]) and not page["records"]:
        return "invalid"
    return "complete" if page["response_complete"] and page["records"] and not page["issues"] else "partial"


def validate_addgene_sequence_page(value) -> dict:
    """Return detached typed data; reject contradictory status/identity joins."""
    try:
        _schema_check(value, ADDGENE_SEQUENCE_PAGE_SCHEMA)
        page = deepcopy(value)
    except (RecursionError, TypeError) as error:
        raise ValueError("addgene_sequence_finite_json_required") from error
    rows = page["records"]
    if not page["source_ref"].strip() or page["parse_status"] != _page_status(page):
        raise ValueError("addgene_sequence_page_relationship")
    issues = {(item["code"], item["record_ordinal"]) for item in page["issues"]}
    for code, ordinal in issues:
        if ordinal is not None and ordinal >= len(rows):
            raise ValueError("addgene_sequence_issue_relationship")
    if (("response_incomplete", None) in issues) != (not page["response_complete"]):
        raise ValueError("addgene_sequence_response_relationship")
    if (("authentication_required", None) in issues) != page["authentication_required"]:
        raise ValueError("addgene_sequence_authentication_relationship")
    if not rows and not any(code in {"representation_unavailable", "invalid_encoding", "invalid_html"} for code, _ in issues):
        raise ValueError("addgene_sequence_empty_relationship")
    locator_owners, previous_first = {}, -1
    for ordinal, row in enumerate(rows):
        if row["record_ordinal"] != ordinal:
            raise ValueError("addgene_sequence_record_ordinal")
        category = _CATEGORIES.get(row["section_id"], ("unknown", "unknown"))
        if (row["source_completeness"], row["source_verification"]) != category:
            raise ValueError("addgene_sequence_category_relationship")
        if set(row["issue_codes"]) != {code for code, owner in issues if owner == ordinal}:
            raise ValueError("addgene_sequence_issue_relationship")
        source_ordinals = [locator["source_element_ordinal"] for locator in row["locators"]]
        if source_ordinals != sorted(source_ordinals) or source_ordinals[0] <= previous_first:
            raise ValueError("addgene_sequence_locator_order")
        previous_first = source_ordinals[0]
        status, text = row["sequence_status"], row["native_sequence_text"]
        if status == "available":
            if text is None or row["sequence"] is None or row["issue_codes"]:
                raise ValueError("addgene_sequence_status_relationship")
            header, sequence, issue = _literal(text)
            if issue is not None or (header, sequence) != (row["native_header"], row["sequence"]):
                raise ValueError("addgene_sequence_literal_relationship")
        elif row["sequence"] is not None:
            raise ValueError("addgene_sequence_status_relationship")
        elif status == "authentication_required":
            if not page["authentication_required"] or row["issue_codes"] != ["authentication_required"] or text is not None:
                raise ValueError("addgene_sequence_authentication_relationship")
        elif status == "download_required":
            if text is not None or row["native_header"] is not None or row["sequence_id"] is None or row["issue_codes"] != ["download_required"] or page["authentication_required"]:
                raise ValueError("addgene_sequence_status_relationship")
        elif status == "invalid":
            if text is None or not row["issue_codes"] or not set(row["issue_codes"]) <= {"empty_literal", "invalid_literal", "incomplete_literal", "ambiguous_sequence_identity", "conflicting_sequence_literals"}:
                raise ValueError("addgene_sequence_status_relationship")
            header, _, literal_issue = _literal(text)
            if header != row["native_header"] or literal_issue is not None and literal_issue not in row["issue_codes"]:
                raise ValueError("addgene_sequence_literal_relationship")
        elif text is not None or row["native_header"] is not None or not row["issue_codes"]:
            raise ValueError("addgene_sequence_status_relationship")
        for locator in row["locators"]:
            key = tuple(locator[name] for name in ("tag", "attribute", "value", "source_element_ordinal"))
            if key in locator_owners:
                raise ValueError("addgene_sequence_duplicate_locator")
            locator_owners[key] = ordinal
            if locator["tag"] != locator["tag"].lower() or locator["attribute"] != locator["attribute"].lower():
                raise ValueError("addgene_sequence_locator_relationship")
            if locator["attribute"] == "href":
                match = _LINK.fullmatch(locator["value"])
                if locator["tag"] != "a" or match is None or match[1] != row["sequence_id"]:
                    raise ValueError("addgene_sequence_locator_relationship")
            elif locator["tag"] != "textarea" or locator["attribute"] != "class" or "copy-from" not in locator["value"].split():
                raise ValueError("addgene_sequence_locator_relationship")
    return page


class _Page(HTMLParser):
    # Textarea is HTML RCDATA. Treat its complete inner content as data so an
    # embedded <tag> cannot disappear and manufacture a valid DNA string.
    CDATA_CONTENT_ELEMENTS = (*HTMLParser.CDATA_CONTENT_ELEMENTS, "textarea")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes, self.stack = [], []

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "ordinal": len(self.nodes),
                "parent": self.stack[-1] if self.stack else None, "children": [],
                "text": [], "closed": tag in _VOID}
        if node["parent"] is not None:
            node["parent"]["children"].append(node)
        self.nodes.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                self.stack[index]["closed"] = True
                del self.stack[index:]
                return

    def handle_data(self, data):
        if self.stack and self.stack[-1]["tag"] == "textarea":
            self.stack[-1]["text"].append(unescape(data))

    def close(self):
        super().close()
        # HTMLParser leaves an unterminated raw-text element in rawdata. Keep
        # the actual prefix, but its missing closing tag remains an issue.
        if self.cdata_elem == "textarea" and self.rawdata:
            self.handle_data(self.rawdata)
            self.rawdata = ""


def _ancestors(node):
    while node is not None:
        yield node
        node = node["parent"]


def _section(node):
    return next((ancestor for ancestor in _ancestors(node) if ancestor["tag"] == "section"), None)


def _link_id(node):
    match = _LINK.fullmatch(node["attrs"].get("href") or "") if node["tag"] == "a" else None
    return match[1] if match else None


def _surrounding_ids(node):
    for ancestor in _ancestors(node):
        if ancestor["tag"] in {"section", "body", "html"}:
            break
        explicit = set()
        for name, value in ancestor["attrs"].items():
            if name == "data-sequence-id" and value and re.fullmatch(r"[0-9]+", value):
                explicit.add(value)
            elif name == "id" and value and (match := _ID.fullmatch(value)):
                explicit.add(match[1])
        if ancestor is node:
            if explicit:
                return explicit
            continue
        pending, ids = [ancestor], explicit
        while pending:
            child = pending.pop()
            sequence_id = _link_id(child)
            if sequence_id is not None:
                ids.add(sequence_id)
            pending.extend(child["children"])
        if ids:
            return ids
    return set()


def _locator(node, attribute):
    return {"tag": node["tag"], "attribute": attribute,
            "value": node["attrs"][attribute], "source_element_ordinal": node["ordinal"]}


def read_addgene_sequences(content: bytes, *, source_ref: str, requested_id: str,
                           response_complete: bool) -> dict:
    """Parse supplied HTML, preserving alternatives without fetching sequences."""
    if type(content) is not bytes:
        raise ValueError("addgene_sequence_content_bytes_required")
    if type(source_ref) is not str or not source_ref.strip():
        raise ValueError("addgene_sequence_source_ref_required")
    if type(requested_id) is not str or re.fullmatch(r"[0-9]+", requested_id) is None:
        raise ValueError("addgene_sequence_requested_id_required")
    if type(response_complete) is not bool:
        raise ValueError("addgene_sequence_response_complete_required")
    page = {"version": "addgene_sequence_page_v1", "source_ref": source_ref,
            "requested_id": requested_id, "response_complete": response_complete,
            "parse_status": "partial", "authentication_required": False,
            "records": [], "issues": []}
    if not response_complete:
        page["issues"].append({"code": "response_incomplete", "record_ordinal": None})
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        page["issues"].append({"code": "invalid_encoding", "record_ordinal": None})
        page["parse_status"] = "invalid"
        return validate_addgene_sequence_page(page)
    parser = _Page()
    try:
        parser.feed(text)
        parser.close()
    except (ValueError, AssertionError):
        page["issues"].append({"code": "invalid_html", "record_ordinal": None})
    page["authentication_required"] = any(
        "anonymous-user-sequence-alert" in (node["attrs"].get("class") or "").split()
        or node["attrs"].get("id") == "anonymous-user-sequence-alert" for node in parser.nodes)
    if page["authentication_required"]:
        page["issues"].append({"code": "authentication_required", "record_ordinal": None})
    candidates, grouped = [], {}

    def make_row(node, sequence_id):
        section = _section(node)
        section_id = section["attrs"].get("id") if section else None
        completeness, verification = _CATEGORIES.get(section_id, ("unknown", "unknown"))
        row = {"record_ordinal": 0, "sequence_id": sequence_id,
               "source_completeness": completeness, "source_verification": verification,
               "section_id": section_id, "native_header": None, "sequence": None,
               "sequence_status": "unavailable", "locators": [],
               "native_sequence_text": None, "issue_codes": []}
        candidates.append((node["ordinal"], row))
        return row

    def key_for(node, sequence_id):
        section = _section(node)
        return (section["ordinal"] if section else None, sequence_id)

    for node in parser.nodes:
        sequence_id = _link_id(node)
        if sequence_id is not None:
            key = key_for(node, sequence_id)
            row = grouped.get(key)
            if row is None:
                row = grouped[key] = make_row(node, sequence_id)
            row["locators"].append(_locator(node, "href"))
    for node in parser.nodes:
        if node["tag"] != "textarea" or "copy-from" not in (node["attrs"].get("class") or "").split():
            continue
        ids = _surrounding_ids(node)
        sequence_id = next(iter(ids)) if len(ids) == 1 else None
        key = key_for(node, sequence_id)
        row = grouped.get(key) if sequence_id is not None else None
        conflict = row is not None and row["native_sequence_text"] is not None
        if row is None or conflict:
            if row is not None:
                row["sequence_status"] = "invalid"
                row["sequence"] = None
                row["issue_codes"].append("conflicting_sequence_literals")
            row = make_row(node, sequence_id)
            if sequence_id is not None and key not in grouped:
                grouped[key] = row
        row["locators"].append(_locator(node, "class"))
        row["native_sequence_text"] = "".join(node["text"])
        header, sequence, issue = _literal(row["native_sequence_text"])
        row["native_header"] = header
        if issue:
            row["issue_codes"].append(issue)
        if not node["closed"]:
            row["issue_codes"].append("incomplete_literal")
        if len(ids) > 1:
            row["issue_codes"].append("ambiguous_sequence_identity")
        if conflict:
            row["issue_codes"].append("conflicting_sequence_literals")
        if row["issue_codes"]:
            row["sequence_status"] = "invalid"
        else:
            row["sequence"], row["sequence_status"] = sequence, "available"
    candidates.sort(key=lambda item: min(locator["source_element_ordinal"] for locator in item[1]["locators"]))
    for ordinal, (_, row) in enumerate(candidates):
        row["record_ordinal"] = ordinal
        row["locators"].sort(key=lambda locator: locator["source_element_ordinal"])
        if row["native_sequence_text"] is None:
            code = "authentication_required" if page["authentication_required"] else "download_required"
            row["sequence_status"] = code
            row["issue_codes"].append(code)
        row["issue_codes"] = list(dict.fromkeys(row["issue_codes"]))
        page["records"].append(row)
        page["issues"].extend({"code": code, "record_ordinal": ordinal} for code in row["issue_codes"])
    if not page["records"]:
        page["issues"].append({"code": "representation_unavailable", "record_ordinal": None})
    page["parse_status"] = _page_status(page)
    return validate_addgene_sequence_page(page)
