import re

SCOPE = 'source_ion_discrimination'

_NUMBER = r'[+−-]?(?:[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?'
# Display-only masks: ion rate/spread values, not pH, ionic concentration,
# membrane voltage or numbers embedded in biological identifiers such as Ec2.
_RATE_DISPLAY = re.compile(r'(?<![A-Za-z0-9_.])(?P<number>' + _NUMBER + r'|10<sup>[+−-]?[0-9]+</sup>)'
    r'(?=\s*(?:ions?\s*/\s*s\b|/\s*(?:s|min)\b|s\s*<sup>[−-]1</sup>|(?:per[_ ]?(?:s|min))\b|s[−-]1\b|-?fold\b))')
_SPREAD_DISPLAY = re.compile(r'(?:±|\+\s*/\s*[-−])\s*(?P<number>' + _NUMBER + ')')
_CONTROL_DISPLAY = re.compile(r'\b(?:recovery|calibration|amount|protein\s+amount|protein\s+concentration|'
    r'contaminant|normalizer|normalization\s+factor|q|g|k|E|u|v)\s*(?:(?:was|is|of)\s+|[:=]\s*)?'
    r'(?P<number>' + _NUMBER + r')(?![A-Za-z0-9_.])')
_FRACTION_DISPLAY = re.compile(r'(?<![A-Za-z0-9_.])(?P<number>' + _NUMBER + r')(?=\s*(?:fraction|dimensionless)\b)')
_DISPLAY_PATTERNS = (_RATE_DISPLAY, _SPREAD_DISPLAY, _CONTROL_DISPLAY, _FRACTION_DISPLAY)

