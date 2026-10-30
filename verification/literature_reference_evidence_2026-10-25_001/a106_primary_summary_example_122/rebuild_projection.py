"""Reproduce the witnessed relevant text representation from original XML.

Default verifies the already retained bytes; --output writes a NEW projection.
This deterministic presentation does not select scientific operands or interpret
the paper. It contains complete selected sections, not the complete article.
"""
from pathlib import Path
import argparse
import hashlib
import json
import textwrap
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
XML = BASE.parent / 'primary_yeag/PMC4664914_original.xml'


def project():
    root = ET.fromstring(XML.read_bytes())
    blocks = []
    for identifier in ('sec2', 'sec5', 'sec9', 'sec12', 'sec17'):
        section = root.find('.//sec[@id="' + identifier + '"]')
        assert section is not None
        blocks.append('SOURCE SECTION ' + identifier)
        for child in section:
            text = ''.join(child.itertext()).strip()
            if text:
                blocks.append(textwrap.fill(text, 115))
    figure = root.find('.//fig[@id="f6"]')
    assert figure is not None
    blocks.extend(('SOURCE FIGURE f6', textwrap.fill(''.join(figure.itertext()).strip(), 115)))
    return ('\n\n'.join(blocks) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    output = parser.parse_args().output
    content = project()
    assert content == (BASE / 'PRIMARY_RELEVANT_TEXT_001.txt').read_bytes()
    if output is not None:
        with output.open('xb') as stream:
            stream.write(content)
    print(json.dumps({'exact_retained_projection_match': True, 'bytes': len(content),
        'sha256': hashlib.sha256(content).hexdigest(), 'original_xml_sha256': hashlib.sha256(XML.read_bytes()).hexdigest()}))
