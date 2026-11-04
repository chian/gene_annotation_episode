"""Finite, original-HTML Km reading; no acquisition or molecular attribution.

Only explicitly balanced HTML is accepted. HTMLParser tokenizes standard HTML
(including void elements and script raw text); this module never repairs a tree,
loads external declarations, evaluates CSS or converts HTML into JATS. Hidden
attributes, common hiding classes and inline visibility styles are excluded;
visibility controlled solely by an external stylesheet is outside this reader.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import math
import re

from .literature_experimental_contracts import ExperimentalContractError

VERSION = "a105_html_quantity_v1"
_VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
_EXCLUDED = frozenset("figure fig figcaption caption table script style template noscript iframe object svg math".split())
_EXCLUDED_CLASSES = frozenset("fig fig-group table-wrap table-wrap-group caption fig-caption figcaption".split())
_HIDDEN_CLASSES = frozenset("hidden d-none sr-only visually-hidden".split())
_NUMBER = r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?"
_SPREAD = rf"(?:\s*(?:\+\s*/\s*[−-]|±)\s*(?P<spread>{_NUMBER}))?"
_KM = r"(?<!\w)(?:apparent\s+)?K\s*_?\s*m(?!\w)"
_UNIT = r"(?P<unit>[µμu]M|nM|mM)(?![\w/⁻^−-])"
_DECLARATION = re.compile(r'''DOCTYPE\s+html(?:\s+(?:PUBLIC\s+(?:"[^"<>\[\]]*"|'[^'<>\[\]]*')\s+(?:"[^"<>\[\]]*"|'[^'<>\[\]]*')|SYSTEM\s+(?:"[^"<>\[\]]*"|'[^'<>\[\]]*')))?\s*''', re.IGNORECASE)
_START_TAG = re.compile(r'''<[A-Za-z][A-Za-z0-9:-]*(?:\s+[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*\s*/?>''')


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


@dataclass(eq=False)
class _Node:
    tag: str
    attrs: dict
    parent: _Node | None
    parts: list = field(default_factory=list)


def _classes(node):
    return set((node.attrs.get("class") or "").lower().split())


def _section(node):
    return node.tag in {"section", "sec"} or (
        node.tag == "div" and bool(_classes(node) & {"section", "sec", "tsec"}))


def _hidden(node):
    if "hidden" in node.attrs or "inert" in node.attrs:
        return True
    if (node.attrs.get("aria-hidden") or "").strip().lower() == "true":
        return True
    if _classes(node) & _HIDDEN_CLASSES:
        return True
    style = node.attrs.get("style") or ""
    # Comments and escapes would require a CSS parser; refuse this visibility
    # ambiguity rather than pretending to evaluate a stylesheet.
    if "/*" in style or "\\" in style:
        _fail("unsupported_inline_style", "source.html")
    for declaration in style.lower().split(";"):
        key, _, value = declaration.partition(":")
        value = value.replace("!important", "").strip()
        if key.strip() == "display" and value == "none":
            return True
        if key.strip() == "visibility" and value in {"hidden", "collapse"}:
            return True
        if key.strip() == "content-visibility" and value == "hidden":
            return True
    return False


def _excluded(node):
    return node.tag in _EXCLUDED or bool(_classes(node) & _EXCLUDED_CLASSES) or _hidden(node)


class _StrictHTML(HTMLParser):
    """Build only the supplied explicit nesting; reject repairs/duplicate attrs."""

    def __init__(self, original):
        super().__init__(convert_charrefs=True)
        self.original = original
        self.line_offsets = [0] + [match.end() for match in re.finditer("\n", original)]
        self.root = _Node("#document", {}, None)
        self.stack = [self.root]
        self.nodes = []
        self.declarations = 0

    def _position(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if not _START_TAG.fullmatch(self.get_starttag_text()):
            _fail("malformed_html", "source.html")
        if len({key for key, _ in attrs}) != len(attrs):
            _fail("duplicate_html_attribute", "source.html")
        if any(not re.fullmatch(r"[^\s\"'<>/=]+", key) for key, _ in attrs):
            _fail("malformed_html", "source.html")
        # Explicit p/section closure prevents an HTML5 parser's implied closure
        # from turning invalid scientific prose into a convenient paragraph.
        if tag in {"p", "section", "div", "figure", "table"} and any(
                node.tag == "p" for node in self.stack):
            _fail("malformed_html", "source.html")
        node = _Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].parts.append(node)
        self.nodes.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        # XML-style empty syntax does not close arbitrary HTML elements.
        foreign_svg = tag == "svg" or any(node.tag == "svg" for node in self.stack)
        if tag not in _VOID and not foreign_svg:
            _fail("malformed_html", "source.html")
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        if not re.compile(r"</" + re.escape(tag) + r"\s*>", re.IGNORECASE).match(
                self.original, self._position()):
            _fail("malformed_html", "source.html")
        if len(self.stack) == 1 or tag in _VOID or self.stack[-1].tag != tag:
            _fail("malformed_html", "source.html")
        self.stack.pop()

    def handle_data(self, data):
        if "\x00" in data or (self.stack[-1].tag not in {"script", "style"}
                              and self.original.startswith("<", self._position())):
            _fail("malformed_html", "source.html")
        self.stack[-1].parts.append(data)

    def handle_comment(self, data):
        if not re.compile(r"<!--(?:(?!--).)*-->", re.DOTALL).match(
                self.original, self._position()):
            _fail("malformed_html", "source.html")
        self.stack[-1].parts.append(" ")

    def handle_decl(self, decl):
        self.declarations += 1
        if self.declarations != 1 or self.stack != [self.root] or not _DECLARATION.fullmatch(decl):
            _fail("html_declarations_not_supported", "source.html")

    def unknown_decl(self, data):
        _fail("html_declarations_not_supported", "source.html")

    def handle_pi(self, data):
        _fail("html_declarations_not_supported", "source.html")


def _paragraph_text(paragraph):
    def flatten(node):
        result = ""
        for part in node.parts:
            if isinstance(part, str):
                addition = part
            elif _excluded(part) or _section(part) or part.tag == "br":
                addition = " "
            else:
                addition = flatten(part)
            # Markup must not concatenate separate numbers into a new value.
            if result and addition and result[-1] in "0123456789." and addition[0] in "0123456789.":
                result += " "
            result += addition
        return result
    return flatten(paragraph)


def _finite(token, field):
    try:
        value = float(token.replace("−", "-"))
    except (ValueError, OverflowError):
        _fail("finite_number_required", field)
    if not math.isfinite(value):
        _fail("finite_number_required", field)
    if value == 0 and any(char in "123456789" for char in token.lower().split("e", 1)[0]):
        _fail("numerical_model_range", field)
    return value


def read_html_quantity(source, *, section_id, paragraph_id, expected_subject,
                       quantity, analyte=None):
    """Read one selected Km expression, with literal subject/analyte checks.

    ``paragraph_id`` is a globally unique original p ID, or the original
    selector ``direct_paragraph:N`` for zero-based visible direct p children of
    the section. Sections are section/sec tags or div.section/div.sec/div.tsec.
    Offsets index retained paragraph Unicode text, including inline sub/sup
    text, excluding hidden/figure/table material. No uncertainty type, replicate
    count or molecular/experimental attribution is inferred from prose.
    """
    if not isinstance(source, dict) or set(source) != {
            "source_ref", "artifact_ref", "html", "representation"}:
        _fail("closed_fields_required", "source")
    for key in ("source_ref", "artifact_ref", "html"):
        _text(source[key], "source." + key)
    if source["representation"] not in ("primary_html", "synthetic_fixture"):
        _fail("unknown_source_representation", "source.representation")
    for key, value in (("section_id", section_id), ("paragraph_id", paragraph_id),
                       ("expected_subject", expected_subject)):
        _text(value, key)
    if quantity != "apparent_km":
        _fail("unsupported_quantity", "quantity")
    _text(analyte, "analyte")
    parser = _StrictHTML(source["html"])
    try:
        parser.feed(source["html"])
        if parser.rawdata:
            _fail("malformed_html", "source.html")
        parser.close()
    except (ValueError, AssertionError) as error:
        if isinstance(error, ExperimentalContractError):
            raise
        raise ExperimentalContractError("malformed_html", "source.html") from error
    if len(parser.stack) != 1:
        _fail("malformed_html", "source.html")
    sections = [node for node in parser.nodes if node.attrs.get("id") == section_id]
    if len(sections) != 1 or not _section(sections[0]):
        _fail("unique_section_required", "section_id")
    section = sections[0]
    selector = re.fullmatch(r"direct_paragraph:(0|[1-9][0-9]*)", paragraph_id)
    if paragraph_id.startswith("direct_paragraph:") and not selector:
        _fail("invalid_paragraph_selector", "paragraph_id")
    if selector:
        paragraphs = [part for part in section.parts if isinstance(part, _Node)
                      and part.tag == "p" and not _excluded(part)]
        if len(selector[1]) > len(str(len(paragraphs))):
            _fail("unique_paragraph_required", "paragraph_id")
        index = int(selector[1])
        if index >= len(paragraphs):
            _fail("unique_paragraph_required", "paragraph_id")
        paragraph = paragraphs[index]
    else:
        paragraphs = [node for node in parser.nodes if node.attrs.get("id") == paragraph_id]
        if len(paragraphs) != 1 or paragraphs[0].tag != "p":
            _fail("unique_paragraph_required", "paragraph_id")
        paragraph = paragraphs[0]
    ids = [node.attrs["id"] for node in parser.nodes if "id" in node.attrs]
    if len(ids) != len(set(ids)):
        _fail("duplicate_html_id", "source.html")
    ancestor = paragraph
    ancestors = []
    while ancestor is not None:
        ancestors.append(ancestor)
        ancestor = ancestor.parent
    if section not in ancestors:
        _fail("paragraph_outside_section", "paragraph_id")
    found = False
    for ancestor in ancestors:
        if _excluded(ancestor):
            _fail("paragraph_not_direct_prose", "paragraph_id")
        if ancestor is section:
            found = True
        elif not found and ancestor is not paragraph and _section(ancestor):
            _fail("paragraph_not_direct_prose", "paragraph_id")
    text = _paragraph_text(paragraph)
    for literal, field_name in ((expected_subject, "expected_subject"), (analyte, "analyte")):
        if not re.search(r"(?<!\w)" + re.escape(literal) + r"(?!\w)", text):
            _fail("subject_not_in_selected_prose" if field_name == "expected_subject"
                  else "analyte_not_in_selected_prose", field_name)
    # Descriptive mentions ("to determine the Km for uptake") are not another
    # measured expression. Count equation/comparator and finite natural-value
    # anchors, including unsupported second analytes and numeric limits.
    measurement_anchor = re.compile(
        rf"{_KM}(?:\s*[=<>≤≥≈~]|\s+of\s+the\s+transporter\s+[\w-]+"
        rf"\s+for\s+[^.;!?]*?\s+was\s+(?:{_NUMBER}|[<>≤≥≈~]|NaN|inf))")
    if len(list(measurement_anchor.finditer(text))) > 1:
        _fail("ambiguous_quantity_expression", "quantity")
    suffix = r"(?=\s*(?:$|[.;,:!?)]|\())"
    literal_analyte = re.escape(analyte) + r"(?!\w)"
    numeric = rf"(?P<value>{_NUMBER}){_SPREAD}\s*{_UNIT}"
    equation = re.compile(rf"{_KM}\s*=\s*{numeric}\s+for\s+{literal_analyte}{suffix}")
    natural = re.compile(
        rf"(?:[Tt]he\s+)?{_KM}\s+of\s+the\s+transporter\s+[\w-]+"
        rf"\s+for\s+{literal_analyte}\s+measured\s+in\s+intact\s+cells\s+was\s+"
        rf"{numeric}{suffix}")
    matches = [match for pattern in (equation, natural) for match in pattern.finditer(text)]
    if not matches:
        _fail("quantity_expression_unavailable", "quantity")
    if len(matches) != 1:
        _fail("ambiguous_quantity_expression", "quantity")
    match = matches[0]
    value = _finite(match["value"], "value")
    spread = _finite(match["spread"], "uncertainty.magnitude") if match["spread"] else None
    if value <= 0:
        _fail("positive_km_required", "value")
    if spread is not None and spread < 0:
        _fail("negative_uncertainty", "uncertainty.magnitude")
    scale = {"uM": 1.0, "nM": .001, "mM": 1000.0}[
        match["unit"].replace("µ", "u").replace("μ", "u")]
    scaled_value = value * scale
    scaled_spread = spread * scale if spread is not None else None
    if (not math.isfinite(scaled_value) or scaled_value == 0
            or scaled_spread is not None and (
                not math.isfinite(scaled_spread) or scaled_spread == 0 and spread != 0)):
        _fail("numerical_model_range", "unit_conversion")
    return {"version": VERSION, "subject": expected_subject, "quantity": quantity,
        "analyte": analyte, "value": scaled_value, "unit": "uM",
        "uncertainty": {"kind": "unspecified" if spread is not None else "unreported",
                        "magnitude": scaled_spread, "count": None, "sampling_basis": "unspecified"},
        "origin": "synthetic" if source["representation"] == "synthetic_fixture" else "reported",
        "normalization": "none",
        "source": {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
            "representation": source["representation"], "section_id": section_id,
            "paragraph_id": paragraph_id, "paragraph_text": text,
            "expression": match.group(), "expression_start": match.start(),
            "expression_end": match.end()}}


__all__ = ["VERSION", "read_html_quantity"]
