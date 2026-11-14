"""Read supplied legacy BLASTP pairwise text without executing or acquiring work.

Every displayed query, description, subject, HSP and traceback remains an ordered
occurrence. Descriptions are not joined to subjects; identifiers are display
tokens only. This module does not bind native occurrences to input proteomes.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import re

from .bvbrc_proteome_directional_contracts import (
    FORMAT, RELEASES, ProteomeDirectionalError, _expected_state, _issue,
    _native_decimal, _native_integer, _required_issues, _validate_source,
    validate_directional_report,
)


_BANNER = re.compile(r"^(\S*BLAST\S*)\s+(\S+)(?:\s+(\[.*\]))?\s*$")
_QUERY_LENGTH = re.compile(r"^\s*\((\S+)\s+letters\)\s*$")
_SUBJECT_LENGTH = re.compile(r"^\s*Length\s*=\s*(\S+)\s*$")
_SCORE_START = re.compile(r"^\s*Score\b")
_COUNTS_START = re.compile(r"^\s*(?:Identities|Positives|Gaps)\b")
_NO_HITS = re.compile(r"^\s*(?:\*+\s*)?No hits found(?:\s*\*+)?\s*$")
_FOOTER_START = re.compile(r"^\s*(?:Database:|Posted date:|Number of |Lambda\s+K\s+H|Gapped$|Matrix:|Gap Penalties:|[Ll]ength of |effective |[TAXS][123]?:|Neighboring words threshold:|Window for multiple hits:)")
_INTEGER_STATS = {
    "Number of letters in database": "database_letters",
    "length of database": "database_letters", "Length of database": "database_letters",
    "Number of sequences in database": "database_sequences",
    "Number of Hits to DB": "hits_to_database", "Number of Sequences": "sequence_counter",
    "Number of extensions": "extensions", "Number of successful extensions": "successful_extensions",
    "Number of HSP's successfully gapped in prelim test": "hsps_successfully_gapped_prelim",
    "Number of HSP's that attempted gapping in prelim test": "hsps_attempted_gapping_prelim",
    "Number of HSP's gapped (non-prelim)": "hsps_gapped_nonprelim",
    "Number of HSP's gapped": "hsps_gapped", "Number of HSP's successfully gapped": "hsps_successfully_gapped",
    "length of query": "query_length", "effective HSP length": "effective_hsp_length",
    "effective length of query": "effective_query_length", "effective length of database": "effective_database_length",
    "effective search space": "effective_search_space", "effective search space used": "effective_search_space_used",
    "T": "neighboring_words_threshold", "Neighboring words threshold": "neighboring_words_threshold",
    "A": "multiple_hits_window", "Window for multiple hits": "multiple_hits_window",
}


def _missing():
    return {"state": "missing", "value": None, "native_text": None, "locations": []}


@dataclass(frozen=True)
class _Line:
    text: str
    start: int
    end: int
    full_end: int

    def offset(self, column):
        return self.start + len(self.text[:column].encode("utf-8"))


class _Reader:
    def __init__(self, content, source, declared_format, report_key):
        self.content = content
        self.lines = []
        self.result = {"version": "bvbrc_proteome_directional_v1", "declared_format": declared_format,
                       "report_key": report_key, "source": deepcopy(source), "parse_state": "failure",
                       "banners": [], "queries": [], "raw_records": [], "issues": []}
        self.binding = source["content"]

    def located(self, a, b):
        return {"source_ref": self.binding["source_ref"], "sha256": self.binding["sha256"],
                "span": {"byte_start": a, "byte_end": b}}

    def span(self, start, end):
        a = self.lines[start].start
        b = self.lines[end - 1].full_end if end > start else a
        return {"byte_start": a, "byte_end": b}

    def cell(self, a, b, kind="string", *, join=False):
        text = self.content[a:b].decode("utf-8")
        value = (_native_integer(text) if kind == "integer" else
                 _native_decimal(text) if kind == "decimal" else
                 " ".join(x.strip() for x in text.splitlines()) if join else text)
        return {"state": "present" if value is not None else "invalid", "value": value,
                "native_text": text, "locations": [self.located(a, b)]}

    def part(self, index, match, group, kind="string"):
        if match is None or match.start(group) < 0:
            return _missing()
        line = self.lines[index]
        return self.cell(line.offset(match.start(group)), line.offset(match.end(group)), kind)

    def whole(self, index):
        line = self.lines[index]
        return self.cell(line.start, line.end)

    def raw(self, kind, start, end):
        if end > start:
            span = self.span(start, end)
            self.result["raw_records"].append({"kind": kind, "locations": [self.located(span["byte_start"], span["byte_end"])]})

    def problem(self, owner, code, scope, q=None, s=None, h=None, start=None, end=None):
        locs = []
        if start is not None:
            span = self.span(start, start + 1 if end is None else end)
            locs = [self.located(span["byte_start"], span["byte_end"])]
        issue = _issue(code, scope, q, s, h, locs)
        if issue not in owner["issues"]:
            owner["issues"].append(issue)

    def text_block(self, start, end, prefix_end):
        first, last = self.lines[start], self.lines[end - 1]
        a = prefix_end
        while a < len(first.text) and first.text[a].isspace():
            a += 1
        b = last.offset(len(last.text.rstrip()))
        return self.cell(first.offset(a), max(first.offset(a), b), join=True)

    def token(self, start, prefix_end):
        match = re.search(r"\S+", self.lines[start].text[prefix_end:])
        if match is None:
            return _missing()
        line = self.lines[start]
        return self.cell(line.offset(prefix_end + match.start()), line.offset(prefix_end + match.end()))

    def identifier(self, header):
        match = re.search(r"\S+", header["native_text"])
        if match is None:
            return _missing()
        start = header["locations"][0]["span"]["byte_start"]
        a = start + len(header["native_text"][:match.start()].encode("utf-8"))
        b = start + len(header["native_text"][:match.end()].encode("utf-8"))
        return self.cell(a, b)

    def read(self):
        if self.result["declared_format"] != FORMAT:
            if self.content:
                self.result["raw_records"].append({"kind": "unparsed_scientific_block", "locations": [self.located(0, len(self.content))]})
            return self.finish()
        try:
            self.content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            self.result["issues"].append(_issue("unsupported_encoding", "report", locations=[self.located(0, len(self.content))]))
            if self.content:
                self.result["raw_records"].append({"kind": "unparsed_scientific_block", "locations": [self.located(0, len(self.content))]})
            return self.finish()
        offset = 0
        for raw in self.content.split(b"\n"):
            if offset == len(self.content) and not raw:
                break
            full_end = min(offset + len(raw) + 1, len(self.content))
            body = raw[:-1] if raw.endswith(b"\r") and full_end > offset + len(raw) else raw
            self.lines.append(_Line(body.decode("utf-8"), offset, offset + len(body), full_end))
            offset = full_end
        banner_at = {}
        for i, line in enumerate(self.lines):
            match = _BANNER.fullmatch(line.text)
            if match:
                ordinal = len(self.result["banners"])
                banner_at[i] = ordinal
                self.result["banners"].append({"ordinal": ordinal, "span": self.span(i, i + 1),
                    "program": self.part(i, match, 1), "release": self.part(i, match, 2),
                    "release_date_text": self.part(i, match, 3), "full_text": self.whole(i)})
        query_at = [i for i, line in enumerate(self.lines) if line.text.startswith("Query=")]
        boundaries = sorted(set(banner_at) | set(query_at) | {len(self.lines)})
        i, banner_ordinal = 0, None
        while i < len(self.lines):
            if i in banner_at:
                banner_ordinal = banner_at[i]
                i += 1
                continue
            if i in query_at:
                end = next(j for j in boundaries if j > i)
                boundary = "next_banner" if end in banner_at else "next_query" if end in query_at else "eof_unconfirmed"
                banner = None if banner_ordinal is None else self.result["banners"][banner_ordinal]
                if banner is not None and (banner["program"]["value"] != "BLASTP" or banner["release"]["value"] not in RELEASES):
                    self.raw("unparsed_scientific_block", i, end)
                else:
                    self.query(i, end, banner_ordinal, boundary)
                i = end
                continue
            text = self.lines[i].text
            if not text.strip():
                i += 1
                continue
            end = i + 1
            if text.startswith("Reference"):
                while end < len(self.lines) and self.lines[end].text.strip() and end not in banner_at and end not in query_at:
                    end += 1
                self.raw("reference", i, end)
            else:
                self.raw("unknown_header", i, end)
                self.problem(self.result, "unparsed_scientific_record", "report", start=i, end=end)
            i = end
        if not self.result["banners"]:
            self.problem(self.result, "missing_banner", "report")
        if not query_at:
            self.problem(self.result, "missing_query_header", "report")
        return self.finish()

    def finish(self):
        for owner, issue in _required_issues(self.result):
            if issue not in owner:
                owner.append(issue)
        self.result["raw_records"].sort(key=lambda r: r["locations"][0]["span"]["byte_start"])
        self.result["parse_state"] = _expected_state(self.result)
        return validate_directional_report(self.result)

    def query(self, start, end, banner_ordinal, boundary):
        ordinal = len(self.result["queries"])
        query = {"ordinal": ordinal, "banner_ordinal": banner_ordinal, "span": self.span(start, end),
                 "header_text": _missing(), "identifier_token": self.token(start, 6), "length": _missing(),
                 "database_headers": [], "descriptions": [], "subjects": [], "no_hits_marker": _missing(),
                 "statistics": [], "boundary": boundary, "issues": []}
        self.result["queries"].append(query)
        i = start + 1
        while i < end and self.lines[i].text.strip() and not _QUERY_LENGTH.fullmatch(self.lines[i].text) and not self.is_section(i):
            i += 1
        query["header_text"] = self.text_block(start, i, 6)
        query["identifier_token"] = self.identifier(query["header_text"])
        if i < end and (match := _QUERY_LENGTH.fullmatch(self.lines[i].text)):
            query["length"] = self.part(i, match, 1, "integer")
            i += 1
        phase = "header"
        while i < end:
            text = self.lines[i].text
            stripped = text.strip()
            if not stripped:
                i += 1
            elif text.startswith("Database:") and phase == "header":
                i = self.database_header(query, i, end)
            elif stripped.startswith("Searching"):
                self.raw("search_progress", i, i + 1)
                i += 1
            elif "Sequences producing significant alignments:" in text:
                phase = "descriptions"
                i += 1
            elif re.fullmatch(r"\s*Score\s+E\s*", text) or re.fullmatch(r"\s*\(bits\)\s+Value\s*", text):
                i += 1
            elif text.startswith(">"):
                phase = "subjects"
                limit = i + 1
                while limit < end and not self.lines[limit].text.startswith(">") and not _FOOTER_START.match(self.lines[limit].text):
                    limit += 1
                self.subject(query, i, limit)
                i = limit
            elif _NO_HITS.fullmatch(text):
                if query["no_hits_marker"]["state"] == "missing":
                    query["no_hits_marker"] = self.whole(i)
                else:
                    self.raw("unparsed_scientific_block", i, i + 1)
                    self.problem(query, "unparsed_scientific_record", "query", ordinal, start=i)
                phase = "footer"
                i += 1
            elif _FOOTER_START.match(text) or phase == "footer":
                self.footer(query, i, end)
                i = end
            elif phase == "descriptions":
                self.description(query, i)
                i += 1
            else:
                self.raw("unknown_header" if phase == "header" else "unparsed_scientific_block", i, i + 1)
                self.problem(query, "unparsed_scientific_record", "query", ordinal, start=i)
                i += 1
        if boundary == "eof_unconfirmed":
            last = next((line.text for line in reversed(self.lines[start:end]) if line.text.strip()), "")
            complete_footer = re.fullmatch(r"\s*S2:\s*\S+\s*\(\s*\S+\s+bits\)\s*", last) is not None
            if complete_footer and self.result["source"]["body_complete"] and self.result["source"]["object_complete"] == "yes":
                query["boundary"] = "eof_complete"

    def is_section(self, i):
        text = self.lines[i].text
        return bool(text.startswith(("Database:", ">", "Query:", "Sbjct:", "Searching")) or
                    _SCORE_START.match(text) or _COUNTS_START.match(text) or _FOOTER_START.match(text) or
                    "Sequences producing significant alignments:" in text or _NO_HITS.fullmatch(text))

    def database_header(self, query, start, end):
        i = start + 1
        count_pattern = re.compile(r"^\s*(\S+)\s+sequences;\s*(\S+)\s+total letters\s*$")
        while i < end and self.lines[i].text.strip() and not count_pattern.fullmatch(self.lines[i].text) and not self.is_section(i):
            i += 1
        header = {"ordinal": len(query["database_headers"]), "span": self.span(start, i),
                  "name_text": self.text_block(start, i, len("Database:")),
                  "sequence_count": _missing(), "letter_count": _missing()}
        if i < end and (match := count_pattern.fullmatch(self.lines[i].text)):
            header["sequence_count"] = self.part(i, match, 1, "integer")
            header["letter_count"] = self.part(i, match, 2, "integer")
            i += 1
            header["span"] = self.span(start, i)
        else:
            self.problem(query, "unparsed_scientific_record", "query", query["ordinal"], start=start, end=i)
        query["database_headers"].append(header)
        return i

    def description(self, query, index):
        desc = {"ordinal": len(query["descriptions"]), "span": self.span(index, index + 1),
                "label": _missing(), "bit_score": _missing(), "evalue": _missing(),
                "ellipsis_suffix": False, "issues": []}
        match = re.fullmatch(r"(\S(?:.*?\S)?)\s+(\S+)\s+(\S+)\s*", self.lines[index].text)
        if match:
            desc["label"] = self.part(index, match, 1)
            desc["bit_score"] = self.part(index, match, 2, "decimal")
            desc["evalue"] = self.part(index, match, 3, "decimal")
        else:
            desc["label"] = self.whole(index)
            self.problem(desc, "malformed_description", "description", query["ordinal"], start=index)
        desc["ellipsis_suffix"] = desc["label"]["value"].endswith("...")
        query["descriptions"].append(desc)

    def subject(self, query, start, end):
        ordinal = len(query["subjects"])
        subject = {"ordinal": ordinal, "span": self.span(start, end), "defline_text": _missing(),
                   "identifier_token": self.token(start, 1), "length": _missing(), "hsps": [], "issues": []}
        query["subjects"].append(subject)
        i = start + 1
        while i < end and self.lines[i].text.strip() and not _SUBJECT_LENGTH.fullmatch(self.lines[i].text) and not self.is_section(i):
            i += 1
        subject["defline_text"] = self.text_block(start, i, 1)
        subject["identifier_token"] = self.identifier(subject["defline_text"])
        if i < end and (match := _SUBJECT_LENGTH.fullmatch(self.lines[i].text)):
            subject["length"] = self.part(i, match, 1, "integer")
            i += 1
        while i < end:
            if not self.lines[i].text.strip():
                i += 1
                continue
            if _SCORE_START.match(self.lines[i].text) or _COUNTS_START.match(self.lines[i].text) or self.lines[i].text.startswith(("Query:", "Sbjct:")):
                limit = i + 1
                saw_traceback = self.lines[i].text.startswith(("Query:", "Sbjct:"))
                while limit < end and not _SCORE_START.match(self.lines[limit].text):
                    if saw_traceback and re.match(r"\s*Identities\b", self.lines[limit].text):
                        break
                    saw_traceback |= self.lines[limit].text.startswith(("Query:", "Sbjct:"))
                    limit += 1
                self.hsp(query, subject, i, limit)
                i = limit
            else:
                self.raw("unparsed_scientific_block", i, i + 1)
                self.problem(subject, "unparsed_scientific_record", "subject", query["ordinal"], ordinal, start=i)
                i += 1

    def hsp(self, query, subject, start, end):
        q, s, h = query["ordinal"], subject["ordinal"], len(subject["hsps"])
        hsp = {"ordinal": h, "span": self.span(start, end), "traceback_blocks": [], "issues": []}
        for name in ("bit_score", "raw_score", "expect", "expect_group_count", "method_text"):
            hsp[name] = _missing()
        for prefix in ("identity", "positive", "gap"):
            for suffix in ("_count", "_denominator", "_printed_percent"):
                hsp[prefix + suffix] = _missing()
        subject["hsps"].append(hsp)
        i = start
        while i < end:
            text = self.lines[i].text
            if not text.strip():
                i += 1
                continue
            if _SCORE_START.match(text):
                for name, pattern, group, kind in (
                    ("bit_score", r"Score\s*=\s*(\S+)", 1, "decimal"),
                    ("raw_score", r"bits\s*\(\s*([^\s)]+)\s*\)", 1, "integer"),
                    ("expect", r"Expect(?:\([^)]*\))?\s*=\s*(\S+?)(?=,\s|\s|$)", 1, "decimal"),
                    ("expect_group_count", r"Expect\(([^)]*)\)", 1, "integer"),
                    ("method_text", r"Method:\s*(.*?)\s*$", 1, "string"),
                ):
                    hsp[name] = self.part(i, re.search(pattern, text), group, kind)
                if not re.fullmatch(r"\s*Score\s*=\s*\S+\s+bits\s*\(\s*\S+\s*\),\s*Expect(?:\([^)]*\))?\s*=\s*\S+(?:,\s*Method:.*)?\s*", text):
                    self.problem(hsp, "malformed_hsp", "hsp", q, s, h, start=i)
                i += 1
            elif _COUNTS_START.match(text):
                for label, prefix in (("Identities", "identity"), ("Positives", "positive"), ("Gaps", "gap")):
                    portion = re.search(label + r"\s*=\s*(.*?)(?=,\s*(?:Identities|Positives|Gaps)\s*=|$)", text)
                    if portion is None:
                        continue
                    if hsp[prefix + "_count"]["state"] != "missing":
                        self.raw("unparsed_scientific_block", i, i + 1)
                        self.problem(hsp, "malformed_hsp", "hsp", q, s, h, start=i)
                        continue
                    match = re.search(label + r"\s*=\s*([^\s/]+)\s*/\s*([^\s(]+)", text)
                    if match:
                        hsp[prefix + "_count"] = self.part(i, match, 1, "integer")
                        hsp[prefix + "_denominator"] = self.part(i, match, 2, "integer")
                    percent = re.search(r"\(\s*([^%()\s]+)\s*%\)", portion.group(1))
                    if percent:
                        line = self.lines[i]
                        a, b = (portion.start(1) + n for n in percent.span(1))
                        hsp[prefix + "_printed_percent"] = self.cell(line.offset(a), line.offset(b), "decimal")
                    if match is None or percent is None:
                        self.problem(hsp, "malformed_hsp", "hsp", q, s, h, start=i)
                if not re.fullmatch(r"\s*(?:Identities|Positives|Gaps)\s*=\s*\S+/\S+\s*\(\S+%\)(?:,\s*(?:Identities|Positives|Gaps)\s*=\s*\S+/\S+\s*\(\S+%\))*\s*", text):
                    self.raw("unparsed_scientific_block", i, i + 1)
                    self.problem(hsp, "malformed_hsp", "hsp", q, s, h, start=i)
                i += 1
            elif text.startswith(("Query:", "Sbjct:")):
                i = self.traceback(hsp, i, end, q, s)
            else:
                self.raw("unparsed_scientific_block", i, i + 1)
                self.problem(hsp, "unparsed_scientific_record", "hsp", q, s, h, start=i)
                i += 1

    def traceback(self, hsp, start, end, q, s):
        block = {"ordinal": len(hsp["traceback_blocks"]), "span": self.span(start, start + 1), "issues": []}
        for key in ("query_start", "query_symbols", "query_end", "midline", "subject_start", "subject_symbols", "subject_end"):
            block[key] = _missing()

        def row(index, side):
            match = re.match(r"(?:Query|Sbjct):\s*(\S+)?(?:\s+(\S+))?(?:\s+(\S+))?", self.lines[index].text)
            if not match:
                return None
            if self.lines[index].text[match.end():].strip():
                self.raw("unparsed_scientific_block", index, index + 1)
                self.problem(block, "unparsed_scientific_record", "hsp", q, s, hsp["ordinal"], start=index)
            for group, suffix, kind in ((1, "_start", "integer"), (2, "_symbols", "string"), (3, "_end", "integer")):
                block[side + suffix] = self.part(index, match, group, kind)
            return match.start(2) if match.start(2) >= 0 else None

        i = start
        if self.lines[i].text.startswith("Query:"):
            column = row(i, "query")
            i += 1
            if i < end and not self.lines[i].text.startswith(("Query:", "Sbjct:")) and not _COUNTS_START.match(self.lines[i].text):
                text = self.lines[i].text
                if column is not None and len(text) >= column and not text[:column].strip():
                    block["midline"] = self.cell(self.lines[i].offset(column), self.lines[i].end)
                    i += 1
                elif i + 1 < end and self.lines[i + 1].text.startswith("Sbjct:"):
                    # A damaged midline must not split adjacent query/subject
                    # rows into different traceback occurrences. Retain its raw
                    # bytes without pretending its sequence column was valid.
                    if text.strip():
                        self.raw("unparsed_scientific_block", i, i + 1)
                        self.problem(block, "unparsed_scientific_record", "hsp", q, s, hsp["ordinal"], start=i)
                    i += 1
            if i < end and self.lines[i].text.startswith("Sbjct:"):
                row(i, "subject")
                i += 1
        else:
            row(i, "subject")
            i += 1
        block["span"] = self.span(start, i)
        hsp["traceback_blocks"].append(block)
        return i

    def statistic(self, query, start, end, kind, label):
        stat = {"ordinal": len(query["statistics"]), "span": self.span(start, end), "kind": kind,
                "native_label": label, "issues": []}
        for key in ("integer_value", "decimal_value", "text_value", "threshold", "bits", "lambda", "k", "h"):
            stat[key] = _missing()
        query["statistics"].append(stat)
        return stat

    def footer(self, query, start, end):
        i, gapped_start = start, None
        while i < end:
            text = self.lines[i].text
            stripped = text.strip()
            if not stripped:
                i += 1
                continue
            if stripped == "Gapped":
                gapped_start = i
                i += 1
                continue
            if re.fullmatch(r"\s*Lambda\s+K\s+H\s*", text):
                j = i + 1
                while j < end and not self.lines[j].text.strip():
                    j += 1
                row = re.fullmatch(r"\s*(\S+)\s+(\S+)\s+(\S+)\s*", self.lines[j].text) if j < end else None
                stat = self.statistic(query, i if gapped_start is None else gapped_start, j + 1 if row else i + 1,
                                      "ka_gapped" if gapped_start is not None else "ka_ungapped", self.whole(i))
                if row:
                    for group, key in enumerate(("lambda", "k", "h"), 1):
                        stat[key] = self.part(j, row, group, "decimal")
                    i = j + 1
                else:
                    self.problem(stat, "unparsed_scientific_record", "statistic", query["ordinal"], start=i)
                    i += 1
                gapped_start = None
                continue
            match = re.fullmatch(r"\s*([^:]+):\s*(.*?)\s*", text)
            if match is None:
                self.raw("unknown_footer", i, i + 1)
                self.problem(query, "unparsed_scientific_record", "query", query["ordinal"], start=i)
                i += 1
                continue
            label, data = match.groups()
            label_cell = self.part(i, match, 1)
            if label == "Database":
                j = i + 1
                while j < end and self.lines[j].text.strip() and not _FOOTER_START.match(self.lines[j].text):
                    j += 1
                stat = self.statistic(query, i, j, "database_name", label_cell)
                stat["text_value"] = self.text_block(i, j, match.start(2))
                i = j
                continue
            if label in {"Posted date", "Matrix"}:
                stat = self.statistic(query, i, i + 1, "database_posted_date" if label == "Posted date" else "matrix", label_cell)
                stat["text_value"] = self.part(i, match, 2)
            elif label == "Gap Penalties":
                for sublabel, kind in (("Existence", "gap_open"), ("Extension", "gap_extend")):
                    stat = self.statistic(query, i, i + 1, kind, label_cell)
                    parsed = re.search(sublabel + r":\s*(\S+?)(?=,\s|\s|$)", text)
                    stat["integer_value"] = self.part(i, parsed, 1, "integer")
                    if parsed is None:
                        self.problem(stat, "unparsed_scientific_record", "statistic", query["ordinal"], start=i)
            elif label in _INTEGER_STATS:
                stat = self.statistic(query, i, i + 1, _INTEGER_STATS[label], label_cell)
                stat["integer_value"] = self.part(i, match, 2, "integer")
            elif re.fullmatch(r"[XS][123]", label) and label != "S3":
                stat = self.statistic(query, i, i + 1, label.lower(), label_cell)
                parsed = re.search(r":\s*(\S+)\s*\(\s*(\S+)\s+bits\)\s*$", text)
                if parsed:
                    stat["integer_value"] = self.part(i, parsed, 1, "integer")
                    stat["bits"] = self.part(i, parsed, 2, "decimal")
                else:
                    self.problem(stat, "unparsed_scientific_record", "statistic", query["ordinal"], start=i)
            elif (threshold := re.fullmatch(r"Number of (sequences|HSP's) better than (\S+?)( without gapping)?", label)):
                kind = "sequences_better_than" if threshold.group(1) == "sequences" else "hsps_better_than_without_gapping"
                stat = self.statistic(query, i, i + 1, kind, label_cell)
                a, b = (match.start(1) + n for n in threshold.span(2))
                stat["threshold"] = self.cell(self.lines[i].offset(a), self.lines[i].offset(b), "decimal")
                stat["integer_value"] = self.part(i, match, 2, "integer")
            else:
                self.raw("unknown_footer", i, i + 1)
                self.problem(query, "unparsed_scientific_record", "query", query["ordinal"], start=i)
            i += 1
        if gapped_start is not None:
            self.raw("unknown_footer", gapped_start, gapped_start + 1)
            self.problem(query, "unparsed_scientific_record", "query", query["ordinal"], start=gapped_start)


def parse_genome_comparison_directional_report(
    content: bytes, *, source: dict, declared_format: str, report_key: str
) -> dict:
    """Return a complete DirectionalReportResult for the supplied bytes.

    Caller errors raise ProteomeDirectionalError before projection. Native
    syntax errors return a partial/failure projection with retained neighbors.
    Hash equality is byte equality, not evidence of task custody or execution.
    """
    for condition, path in (
        (type(content) is bytes, "/content"),
        (type(declared_format) is str and bool(declared_format.strip()), "/declared_format"),
        (type(report_key) is str and bool(report_key.strip()), "/report_key"),
    ):
        if not condition:
            raise ProteomeDirectionalError("directional_argument_invalid", path)
    _validate_source(source)
    if hashlib.sha256(content).hexdigest() != source["content"]["sha256"]:
        raise ProteomeDirectionalError("directional_digest_mismatch", "/source/content/sha256")
    if len(content) != source["content"]["byte_count"]:
        raise ProteomeDirectionalError("directional_byte_count_mismatch", "/source/content/byte_count")
    return _Reader(content, source, declared_format, report_key).read()


__all__ = ["ProteomeDirectionalError", "parse_genome_comparison_directional_report"]
