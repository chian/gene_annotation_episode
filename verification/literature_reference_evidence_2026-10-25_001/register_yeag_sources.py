"""Register retained original sources and explicit inspected visual transcriptions.

No source search, inference or investigation choices occur here. The numerical
figure labels are manual transcriptions, not OCR or new band measurements.
"""
from pathlib import Path
from gene_annotation_episode.acquisition import article_details
from gene_annotation_episode.domain import canonical


def register_sources(store, directory):
    directory=Path(directory)
    xml=(directory/'PMC4664914_original.xml').read_bytes()
    details=article_details(xml)
    text='\n\n'.join(f"[paragraph {row['paragraph_index']}]\n{row['text']}" for row in details['sections'])
    def publish(content,provider,uri=None,parents=(),text_content=None):
        artifact=store.artifact(content,'application/octet-stream')
        return store.put('source',{'provider':provider,'accession':None,'uri':uri,
            'artifact_ref':artifact,'text_ref':store.artifact(text_content,'text/plain') if text_content else None,
            'request_ref':None,'version':None,'retrieved_at':None,'parent_source_refs':list(parents)},origin='caller')
    paper=publish(xml,'retained_primary_jats','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4664914/fullTextXML',text_content=text)
    image=publish((directory/'srep17524-f3.jpg').read_bytes(),'retained_primary_figure',
        'https://pmc-oa-opendata.s3.amazonaws.com/PMC4664914.1/srep17524-f3.jpg',parents=[paper['id']])
    sources=[paper['id'],image['id']]
    transcriptions={}
    for variant,label,box,reference_box in [
        ('K116A','0.64',[161,539,193,557],[100,539,129,557]),
        ('R232A','0.48',[207,539,242,557],[100,539,129,557]),
        ('K426A','1.12',[533,539,567,557],[478,539,510,557]),
        ('Y382stop','0.96',[577,539,611,557],[478,539,510,557])]:
        record={'version':'relative_visual_signal_v1','subject':'YeaG','variant':variant,'reference':'wild-type levels',
            'observations':[{'printed_label':label,'reference_printed_label':'1.0',
                'original_source_ref':image['id'],'original_artifact_ref':image['artifact_ref'],
                'image_region':box,'reference_image_region':reference_box}]}
        row=publish(canonical(record),'retained_visual_transcription',parents=[image['id']])
        transcriptions[variant]=row['id']
        sources.append(row['id'])
    return {'source_refs':sources,'paper_ref':paper['id'],'image_ref':image['id'],
            'visual_transcriptions':transcriptions,'source_origin':'retained_primary_sources_and_manual_visual_labels',
            'publication_identifiers':details['publication_identifiers']}
