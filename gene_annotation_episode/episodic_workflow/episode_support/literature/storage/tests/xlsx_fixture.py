"""A real XLSX package written with the standard library: worksheets of literal cells."""
from io import BytesIO
from xml.sax.saxutils import escape
import zipfile

MEDIA_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
_OFFICE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/></Relationships>' % _OFFICE)


def _sheet(rows):
    body = ''
    for number in sorted(rows):
        cells = ''
        for column in sorted(rows[number]):
            value = rows[number][column]
            address = column + str(number)
            if value is None:
                cells += '<c r="%s"/>' % address
            elif isinstance(value, str):
                cells += '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (address, escape(value))
            else:
                cells += '<c r="%s"><v>%s</v></c>' % (address, value)
        body += '<row r="%d">%s</row>' % (number, cells)
    return ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData>%s</sheetData></worksheet>' % body)


def workbook(sheets):
    """The bytes of a workbook of ``sheets``: ``{sheet name: {row number: {column letter: str or number}}}``."""
    names = list(sheets)
    book = ('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="%s"><sheets>%s</sheets></workbook>' % (_OFFICE, ''.join(
                '<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': '&quot;'}), i + 1, i + 1)
                for i, name in enumerate(names))))
    relationships = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s'
                     '</Relationships>' % ''.join('<Relationship Id="rId%d" Type="%s/worksheet" Target="worksheets/sheet%d.xml"/>'
                                                  % (i + 1, _OFFICE, i + 1) for i in range(len(names))))
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('_rels/.rels', _RELS)
        archive.writestr('xl/workbook.xml', book)
        archive.writestr('xl/_rels/workbook.xml.rels', relationships)
        for i, name in enumerate(names):
            archive.writestr('xl/worksheets/sheet%d.xml' % (i + 1), _sheet(sheets[name]))
    return buffer.getvalue()
