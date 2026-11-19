"""A106 native JSON token preservation for received NCBI responses."""
import json
import math
MAX_SAFE_INTEGER = 9007199254740991

def _require(condition):
    if not condition:
        raise ValueError("ncbi_native_json_value_invalid")

def _issue(code, pointer):
    return {"code": code, "pointer": pointer}


def _unique_issues(issues):
    result, seen = [], set()
    for row in issues:
        key = row["code"], row["pointer"]
        if key not in seen:
            result.append(row)
            seen.add(key)
    return result


class _Members:
    def __init__(self, pairs):
        self.pairs = pairs


class _NumberToken:
    def __init__(self, token):
        self.token = token
        self.integer = "." not in token and "e" not in token.lower()


def _number_value(number):
    token = number.token
    try:
        if number.integer:
            if len(token.lstrip("-")) > 16:
                return None, False
            value = int(token)
            return (value, True) if abs(value) <= MAX_SAFE_INTEGER and str(value) == token else (None, False)
        value = float(token)
        if math.isfinite(value) and json.dumps(value, allow_nan=False) == token:
            return value, True
    except (ValueError, OverflowError):
        pass
    return None, False


def _analyse(node, pointer="/native_document"):
    """Return one reversible native representation, with exact token locations."""
    if isinstance(node, _Members):
        native, members, issues, names, required = {}, [], [], set(), False
        for index, (name, child) in enumerate(node.pairs):
            name.encode("utf-8")
            location = pointer + "/members/" + str(index)
            value, document, child_issues, child_required = _analyse(child, location + "/value")
            members.append({"name": name, "value": document})
            issues.extend(child_issues)
            required |= child_required
            if name in names:
                required = True
                issues.append(_issue("native_duplicate_member", location))
            else:
                native[name] = value
                names.add(name)
        return native, {"kind": "object", "members": members}, issues, required
    if isinstance(node, list):
        native, items, issues, required = [], [], [], False
        for index, child in enumerate(node):
            value, document, child_issues, child_required = _analyse(child, pointer + "/items/" + str(index))
            native.append(value)
            items.append(document)
            issues.extend(child_issues)
            required |= child_required
        return native, {"kind": "array", "items": items}, issues, required
    if isinstance(node, _NumberToken):
        value, safe = _number_value(node)
        return value, {"kind": "number", "token": node.token}, ([] if safe else [
            _issue("native_number_token_required", pointer)]), not safe
    if isinstance(node, str):
        node.encode("utf-8")
        return node, {"kind": "string", "value": node}, [], False
    if type(node) is bool:
        return node, {"kind": "boolean", "value": node}, [], False
    _require(node is None)
    return None, {"kind": "null", "value": None}, [], False


def _parse(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return None, "decode_failed", "invalid_native_utf8", None, None, []
    def constant(_token):
        raise ValueError("non_json_constant")
    try:
        node = json.loads(text, parse_int=_NumberToken, parse_float=_NumberToken,
            object_pairs_hook=_Members, parse_constant=constant)
    except (ValueError, RecursionError, OverflowError):
        return None, "decode_failed", "invalid_native_json", None, None, []
    try:
        native, document, issues, required = _analyse(node)
    except (UnicodeError, RecursionError):
        return None, "decode_failed", "invalid_native_unicode", None, None, []
    return (node, "json_document", None, None, document, issues) if required else (
        node, "json", None, native, None, [])


def _from_plain(value):
    # Native record parsers may retain dict subclasses, such as Biopython's
    # defaultdict structured comments. Preserve their existing members without
    # invoking a default factory or leaving an opaque mapping in the tree.
    if isinstance(value, dict):
        return _Members([(name, _from_plain(child)) for name, child in value.items()])
    if type(value) is list:
        return [_from_plain(child) for child in value]
    if type(value) in (int, float):
        return _NumberToken(json.dumps(value, allow_nan=False))
    return value


