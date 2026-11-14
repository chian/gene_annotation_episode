from __future__ import annotations
import re
from urllib.parse import urlsplit
BASE_URL = 'https://batch.rfam.org'
JOB = re.compile('infernal_cmscan-[A-Za-z0-9_-]+')

def result_url(job_id: str) -> str:
    if not isinstance(job_id, str) or not JOB.fullmatch(job_id):
        raise ValueError('rfam_job_identity_invalid')
    return BASE_URL + '/result/' + job_id

def validate_result_url(url: str, job_id: str) -> None:
    if not isinstance(url, str) or urlsplit(url) != urlsplit(result_url(job_id)):
        raise ValueError('rfam_result_url_identity_conflict')
