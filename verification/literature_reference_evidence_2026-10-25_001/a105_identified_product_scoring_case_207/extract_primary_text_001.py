"""Reproduce already retained readable article text from public original HTML."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib,json
class Article(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.active=False;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='article':self.active=True
        if self.active and tag in ('p','h1','h2','h3','h4','tr','figcaption'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag=='article':self.active=False
        if self.active and tag in ('p','h1','h2','h3','h4','tr','figcaption'):self.parts.append('\n')
        elif self.active and tag in ('td','th'):self.parts.append(' | ')
    def handle_data(self,text):
        if self.active:self.parts.append(text)
base=Path(__file__).resolve().parent
raw=(base/'acquisition_001.bin').read_bytes()
p=Article();p.feed(raw.decode('utf8'));derived=''.join(p.parts)
stored=(base/'primary_read_001.txt').read_text()
assert derived==stored
print(json.dumps({'reproduced':True,'source_sha256':hashlib.sha256(raw).hexdigest(),'readable_sha256':hashlib.sha256(derived.encode()).hexdigest(),'readable_characters':len(derived),'writes':0}))
