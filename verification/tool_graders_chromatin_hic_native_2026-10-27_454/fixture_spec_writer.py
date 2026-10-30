"""Packet-only full HIC v9 fixture serializer from the official byte specification.

This is an explicitly synthetic format-fixture writer, not hictk or production
parser code. The entire file (header, zlib block, zoom/master indexes and footer)
is emitted to disk and must then pass independent official-reader checks.
Only tiny cis BP matrices are supported; no scientific inference is performed.
"""
import hashlib
import math
import struct
import zlib

def pack(fmt,*values): return struct.pack('<'+fmt,*values)
def string(value): return value.encode('utf-8')+b'\0'

def write(path,rows,*,float_counts=True,x_int=True,y_int=True,dense=False,zero_blocks=False,weights=None):
    assert all(0<=x<=y<4 for x,y,value in rows)
    vfmt='f' if float_counts else 'h'; xfmt='i' if x_int else 'h'; yfmt='i' if y_int else 'h'
    payload=pack('iiiBBBB',len(rows),0,0,int(float_counts),int(x_int),int(y_int),2 if dense else 1)
    if dense:
        slots={(x,y):value for x,y,value in rows}; assert len(slots)==len(rows)
        payload+=pack('ih',16,4)
        for y in range(4):
            for x in range(4): payload+=pack(vfmt,slots.get((x,y),float('nan') if float_counts else -32768))
    else:
        ys=sorted({y for x,y,value in rows})
        payload+=pack(yfmt,len(ys))
        for y in ys:
            cells=sorted((x,value) for x,yy,value in rows if yy==y)
            payload+=pack(yfmt,y)+pack(xfmt,len(cells))
            for x,value in cells: payload+=pack(xfmt,x)+pack(vfmt,value)
    compressed=b'' if zero_blocks else zlib.compress(payload,9)
    def header(footer,nvi,nvi_size):
        return (b'HIC\0'+pack('iq',9,footer)+string('synthetic_format_fixture')+pack('qq',nvi,nvi_size)+
                pack('i',1)+string('software')+string('packet454_fixture_spec_writer')+
                pack('i',1)+string('chrA')+pack('q',40)+pack('ii',1,10)+pack('i',0))
    head=header(0,0,0); blockpos=len(head); matrixpos=blockpos+len(compressed)
    total=sum(value for x,y,value in rows if math.isfinite(value))
    zoom=string('BP')+pack('ififfiiii',0,total,0,0.0,0.0,10,5,1,0 if zero_blocks else 1)
    if not zero_blocks: zoom+=pack('iqi',0,blockpos,len(compressed))
    matrix=pack('iii',0,0,1)+zoom
    footerpos=matrixpos+len(matrix)
    master=pack('i',1)+string('0_0')+pack('qi',matrixpos,len(matrix))
    expected=pack('i',0); normalized_expected=pack('i',0)
    footer=pack('q',len(master)+len(expected))+master+expected+normalized_expected
    nvipos=footerpos+len(footer)
    if weights is None:
        nvi=pack('i',0); vector=b''
    else:
        vector=pack('q',len(weights))+b''.join(pack('f',v) for v in weights)
        prefix=pack('i',1)+string('SYNTHETIC_DIVISIVE')+pack('i',0)+string('BP')+pack('i',10)
        nvi=prefix+pack('qq',nvipos+len(prefix)+16,len(vector))
    head=header(footerpos,nvipos,len(nvi))
    data=head+compressed+matrix+footer+nvi+vector
    path.write_bytes(data)
    return {'file_sha256':hashlib.sha256(data).hexdigest(),'file_size':len(data),'writer':'packet454_fixture_spec_writer',
            'header_size':len(head),'block_position':None if zero_blocks else blockpos,'compressed_size':len(compressed),'matrix_position':matrixpos,'matrix_size':len(matrix),'footer_position':footerpos,'normalization_index_position':nvipos,'normalization_index_size':len(nvi),
            'payload_sha256':None if zero_blocks else hashlib.sha256(payload).hexdigest(),'n_records':len(rows),'float_counts':float_counts,'x_int':x_int,'y_int':y_int,'representation':2 if dense else 1,'zero_blocks':zero_blocks}
