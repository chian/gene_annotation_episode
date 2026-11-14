"""Original finite reported-ratio lexical predicates; no source acquisition or interpretation."""
import re

_NUMBER = r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?"
_PERCENT = re.compile(
    rf"(?<![\w.,+−-])(?P<number>{_NUMBER})\s*%\s*\((?P<label>[^()]*)\)"
)
_LIMIT_PREFIX = re.compile(
    r"(?:<=|>=|[<>≤≥~≈±–—−-]|\b(?:(?:less|greater|more|fewer)\s+than|"
    r"at\s+most|at\s+least|up\s+to|below|above|approximately|about|circa|"
    r"roughly|around|between|from|not(?:\s+at)?))\s*$", re.IGNORECASE,
)
_RANGE_PREFIX = re.compile(
    rf"{_NUMBER}\s*%?\s*(?:to|and)\s*$", re.IGNORECASE,
)


def _contains_literal(text, literal):
    return re.search(r"(?<!\w)" + re.escape(literal) + r"(?!\w)", text) is not None


def _sentence_end(text, start):
    """Find finite prose punctuation, preserving decimal points in later ratios.

    This is deliberately not a general sentence parser. A period immediately
    before a digit belongs to a decimal token; other periods, ! and ? end this
    reader's comparison span. Abbreviations requiring inference are unsupported.
    """
    for position in range(start, len(text)):
        char = text[position]
        if char in "!?" or char == "." and not text[position + 1:position + 2].isdigit():
            return position
    return len(text)


