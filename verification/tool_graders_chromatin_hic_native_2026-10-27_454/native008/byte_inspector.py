"""Independent tiny-file audit decoder, authored from the official v9 byte spec.

This packet diagnostic is not the production H1 reader and imports no production
code. It reads complete small fixture bytes, retaining decoded block payloads.
It deliberately does not expose a scientific-sheet/parser interface.
"""
from pathlib import Path
import hashlib
import math
import struct
import zlib

def sha(data): return hashlib.sha256(data).hexdigest()
def number(value):
    if isinstance(value,float) and not math.isfinite(value):
        return 'NaN' if math.isnan(value) else ('+Inf' if value>0 else '-Inf')
    return value

class Cursor:
    def __init__(self,data,pos=0): self.data=data; self.pos=pos
    def get(self,fmt):
        fmt='<'+fmt; size=struct.calcsize(fmt)
        if self.pos+size>len(self.data): raise ValueError('short_field')
        value=struct.unpack_from(fmt,self.data,self.pos)
        self.pos+=size
        return value[0] if len(value)==1 else value
    def string(self):
        stop=self.data.index(b'\0',self.pos)
        value=self.data[self.pos:stop].decode('utf-8'); self.pos=stop+1
        return value

def inspect(path,outdir):
    path=Path(path); outdir=Path(outdir); outdir.mkdir(exist_ok=True)
    data=path.read_bytes(); c=Cursor(data)
    assert data[:4]==b'HIC\0'; c.pos=4
    version=c.get('i'); assert version==9
    footer=c.get('q'); genome=c.string(); nvi=c.get('q'); nvi_size=c.get('q')
    attributes=[(c.string(),c.string()) for _ in range(c.get('i'))]
    chroms=[{'index':i,'name':c.string(),'native_length':c.get('q')} for i in range(c.get('i'))]
    resolutions=[c.get('i') for _ in range(c.get('i'))]
    frag=[c.get('i') for _ in range(c.get('i'))]; assert not frag
    result={'file':str(path),'size_bytes':len(data),'sha256':sha(data),'version':version,
            'genome_id':genome,'footer_position':footer,'normalization_index_position':nvi,
            'normalization_index_length':nvi_size,'attributes':attributes,'chromosomes':chroms,
            'bp_resolutions':resolutions,'frag_resolutions':frag,'header_end':c.pos,'matrices':[],'normalization_vectors':[]}
    c.pos=footer; result['footer_nbytes_v5']=c.get('q'); count=c.get('i')
    entries=[{'key':c.string(),'position':c.get('q'),'size':c.get('i')} for _ in range(count)]
    result['master_index_entries']=entries
    for entry in entries:
        c.pos=entry['position']; matrix={'key':entry['key'],'position':c.pos,'chr1':c.get('i'),'chr2':c.get('i'),'zooms':[]}
        zoom_count=c.get('i')
        for _ in range(zoom_count):
            start=c.pos
            zoom={'unit':c.string(),'resolution_index':c.get('i'),'sum_counts':number(c.get('f')),
                  'occupied_cell_count':c.get('i'),'percent5':number(c.get('f')),'percent95':number(c.get('f')),
                  'resolution':c.get('i'),'block_bin_count':c.get('i'),'block_column_count':c.get('i'),'blocks':[]}
            block_count=c.get('i'); zoom['declared_block_count']=block_count
            index=[{'block_id':c.get('i'),'position':c.get('q'),'compressed_size':c.get('i')} for _ in range(block_count)]
            next_pos=c.pos; zoom['zoom_index_position']=start; zoom['zoom_index_size']=next_pos-start
            for block in index:
                packed=data[block['position']:block['position']+block['compressed_size']]
                assert len(packed)==block['compressed_size']
                decompressor=zlib.decompressobj(); payload=decompressor.decompress(packed)+decompressor.flush()
                assert decompressor.eof and not decompressor.unused_data and not decompressor.unconsumed_tail
                block.update(compressed_sha256=sha(packed),decoded_sha256=sha(payload),decoded_size=len(payload),zlib_eof=True)
                name=f"matrix-{entry['key']}-r{zoom['resolution']}-block-{block['block_id']}.payload"
                (outdir/name).write_bytes(payload); block['decoded_payload']=str(outdir/name)
                p=Cursor(payload); n=p.get('i'); xo=p.get('i'); yo=p.get('i'); vf,xf,yf,rep=p.get('BBBB')
                assert vf in (0,1) and xf in (0,1) and yf in (0,1) and rep in (1,2)
                valuefmt='f' if vf else 'h'; xfmt='i' if xf else 'h'; yfmt='i' if yf else 'h'
                block.update(n_records=n,x_offset=xo,y_offset=yo,use_float=vf,use_int_x=xf,use_int_y=yf,representation=rep)
                records=[]; fillers=[]
                if rep==1:
                    for row in range(p.get(yfmt)):
                        y=yo+p.get(yfmt)
                        for col in range(p.get(xfmt)):
                            x=xo+p.get(xfmt); value=p.get(valuefmt)
                            records.append({'x':x,'y':y,'value':number(value),'ordinal':len(records)})
                else:
                    nslots=p.get('i'); width=p.get('h'); assert nslots>=0 and width>0
                    block.update(dense_slots=nslots,dense_width=width)
                    for ordinal in range(nslots):
                        value=p.get(valuefmt); x=xo+ordinal%width; y=yo+ordinal//width
                        filler=(math.isnan(value) if vf else value==-32768)
                        if filler: fillers.append({'ordinal':ordinal,'x':x,'y':y})
                        else: records.append({'x':x,'y':y,'value':number(value),'ordinal':ordinal})
                assert p.pos==len(payload) and len(records)==n
                block.update(payload_consumed_exactly=True,records=records,filler_slots=fillers,decoded_record_count=len(records))
                zoom['blocks'].append(block)
            c.pos=next_pos; matrix['zooms'].append(zoom)
        assert c.pos==entry['position']+entry['size']
        result['matrices'].append(matrix)
    if nvi>0 and nvi_size>0:
        c.pos=nvi; entries=[]
        for _ in range(c.get('i')):
            entries.append({'type':c.string(),'chromosome_index':c.get('i'),'unit':c.string(),'resolution':c.get('i'),'position':c.get('q'),'size':c.get('q')})
        assert c.pos==nvi+nvi_size
        for entry in entries:
            c.pos=entry['position']; nv=c.get('q'); entry['n_values']=nv
            entry['values']=[number(c.get('f')) for _ in range(nv)]
            assert c.pos==entry['position']+entry['size']
            result['normalization_vectors'].append(entry)
    return result
