"""Store-free spreadsheet worker executed through the protected job lifecycle."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

from .spreadsheet_tools import read_workbook


def main():
    request_path, output = map(Path, sys.argv[1:])
    request = json.loads(request_path.read_text())
    try:
        result = read_workbook(request['path'], request['operation'], request['arguments'], output.parent)
    except (ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        output.write_text(json.dumps({'code': 'xlsx_source_or_selection_invalid',
            'exception_type': type(error).__name__, 'detail': str(error)}))
        return 2
    output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
