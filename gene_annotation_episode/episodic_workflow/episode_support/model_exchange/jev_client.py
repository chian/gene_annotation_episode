"""The TypeSafe Jev client: calibrated yes/no probabilities ("nouls") for named questions over one shared state.

A minimal port of nano-graphrag's ``question_pipeline/utilities/model.py`` (``JevDecisionClient`` with its
``nouls``, ``nouls_request_token_count`` and the ``JEV_*`` budgets). Differences, each forced by this repository:

- Credentials. nano-graphrag reads ``TYPESAFE_API_KEY`` from the process environment; the workflow launcher passes no
  caller environment, so the client reads ``TYPESAFE_API_KEY`` at run time from the repository's own ``.env`` file
  (gitignored, private; one ``NAME=value`` per line). The value is held only inside the client and sent only in the
  request's ``Authorization`` header; it is never logged, returned, copied or put in an exception.
- Token counts. nano-graphrag counts ``o200k_base`` tokens with ``tiktoken``, which this repository does not install.
  Every ``o200k_base`` token decodes to at least one UTF-8 byte, so the UTF-8 byte length of a text is an upper bound
  of its token count. The budgets below are checked against that bound (times nano-graphrag's calibration
  multiplier), so a request that passes here is within Jev's limits; requests are only smaller than nano-graphrag's.
- Failures. The repository's model provider retries nothing and sets no time limit (AGENTS.md); neither does this
  client. Any HTTP or response error raises ``JevCallError``.

The client is the provider boundary only: it returns probabilities and never routes, selects or credits."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path

import requests

JEV_API_ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
JEV_KEY_VARIABLE = 'TYPESAFE_API_KEY'
# The repository's own .env (this file is gene_annotation_episode/episodic_workflow/episode_support/model_exchange/).
JEV_KEY_FILE = Path(__file__).resolve().parents[4] / '.env'
JEV_MODEL = 'jev-1.13.0'
# Jev shares state across questions: the batch and each state/question pair have separate limits
# (nano-graphrag: https://docs.typesafe.ai/models).
JEV_REQUEST_TOKEN_BUDGET = 64_000
JEV_EVALUATION_TOKEN_BUDGET = 32_000
# nano-graphrag: captured Jev 1.13 requests reported 1.153--1.225 times the local o200k_base count.
JEV_TOKEN_ESTIMATE_MULTIPLIER = 1.25
# nano-graphrag: binding-side packing leaves room for provider serialization/tokenizer variance.
JEV_TOKEN_HEADROOM = 10_000
JEV_TOKEN_BOUND = 'utf8_bytes_upper_bound_of_o200k_base_tokens'


class JevCallError(RuntimeError):
    """A Jev call failed (credential, transport, HTTP status or response shape). Carries no secret."""


def token_bound(value):
    """An upper bound of the ``o200k_base`` token count of text or of compact serialized JSON: its UTF-8 bytes."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, allow_nan=False,
                                                            separators=(',', ':'), default=str)
    return len(text.encode('utf-8'))


def jev_token_estimate(value):
    """nano-graphrag's ``jev_token_estimate`` over the byte bound."""
    return math.ceil(token_bound(value) * JEV_TOKEN_ESTIMATE_MULTIPLIER)


def window_text(text, *, budget):
    """Split ``text`` losslessly into consecutive pieces of at most ``budget`` bounded tokens (UTF-8 bytes), cut at
    character boundaries (nano-graphrag's ``token_window_text`` over the byte bound)."""
    if not text:
        return []
    if budget <= 0:
        raise ValueError('token window budget must be positive')
    pieces, current, size = [], [], 0
    for character in text:
        width = len(character.encode('utf-8'))
        if current and size + width > budget:
            pieces.append(''.join(current))
            current, size = [], 0
        current.append(character)
        size += width
    if current:
        pieces.append(''.join(current))
    if ''.join(pieces) != text:
        raise ValueError('token windows did not preserve the complete text')
    return pieces


@dataclass(frozen=True)
class JevResponse:
    model: str
    answers: Mapping
    input_tokens: int
    output_tokens: int
    attempts: int


@dataclass(frozen=True)
class JevNoulVectorDecision:
    probabilities: Mapping
    response: JevResponse


def _probability(answer, name):
    if not isinstance(answer, Mapping) or answer.get('type') != 'noul':
        raise JevCallError(f'jev_response_omitted_noul:{name}')
    value = answer.get('noul')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
        raise JevCallError(f'jev_noul_probability_invalid:{name}')
    return float(value)


class JevDecisionClient:
    """nano-graphrag's ``JevDecisionClient``: Jev's native ``state + typed questions`` contract."""

    def __init__(self, *, api_key, endpoint=JEV_API_ENDPOINT, model=JEV_MODEL):
        if not isinstance(api_key, str) or not api_key.strip():
            raise JevCallError('jev_api_key_empty')
        self.__api_key = api_key.strip()
        self.endpoint, self.model = endpoint, model

    def __repr__(self):
        return f'<JevDecisionClient model={self.model!r} endpoint={self.endpoint!r}>'

    @classmethod
    def from_repository_env(cls):
        """The client with ``TYPESAFE_API_KEY`` read now from the repository's ``.env``. A missing file, or a file
        without exactly one non-empty ``TYPESAFE_API_KEY=`` line, raises ``JevCallError`` naming what is missing
        (never a value)."""
        try:
            lines = JEV_KEY_FILE.read_text(encoding='utf-8').splitlines()
        except OSError as error:
            raise JevCallError(f'jev_key_file_unavailable:{type(error).__name__}:{JEV_KEY_FILE}') from None
        values = [line.split('=', 1)[1].strip() for line in lines
                  if line.split('=', 1)[0].strip() == JEV_KEY_VARIABLE and '=' in line]
        if len(values) != 1 or not values[0]:
            raise JevCallError(f'jev_key_unavailable:{JEV_KEY_VARIABLE}:lines={len(values)}:{JEV_KEY_FILE}')
        return cls(api_key=values[0])

    @staticmethod
    def _noul_questions(questions):
        if not isinstance(questions, Mapping) or not questions:
            raise ValueError('Jev nouls requires at least one named question')
        out = {}
        for name, declaration in questions.items():
            question = {'type': 'noul', 'instructions': declaration['instructions']}
            if declaration.get('criteria') is not None:
                question['criteria'] = dict(declaration['criteria'])
            out[str(name)] = question
        return out

    def _payload(self, state, questions):
        return {'state': state, 'model': self.model, 'questions': dict(questions)}

    def nouls_request_token_count(self, *, state, questions, largest_evaluation=False):
        """The estimated request tokens, or (``largest_evaluation``) the shared state plus the longest question."""
        typed = self._noul_questions(questions)
        if largest_evaluation:
            return math.ceil((token_bound(state) + max(token_bound(question) for question in typed.values()))
                             * JEV_TOKEN_ESTIMATE_MULTIPLIER)
        return jev_token_estimate(self._payload(state, typed))

    def _post(self, payload):
        try:
            response = requests.post(self.endpoint, json=payload, headers={
                'Authorization': 'Bearer ' + self.__api_key, 'Content-Type': 'application/json'})
        except requests.RequestException as error:
            raise JevCallError('jev_transport_failed:' + type(error).__name__) from None
        if response.status_code >= 400:
            raise JevCallError(f'jev_http_status:{response.status_code}:{response.text.strip()[:2000]}')
        try:
            body = response.json()
        except ValueError:
            raise JevCallError('jev_response_not_json') from None
        return body

    def evaluate(self, *, state, questions):
        """One Jev request; every requested answer is validated before anything is returned."""
        payload = self._payload(state, questions)
        request_tokens = jev_token_estimate(payload)
        evaluation_tokens = math.ceil((token_bound(state) + max(token_bound(q) for q in questions.values()))
                                      * JEV_TOKEN_ESTIMATE_MULTIPLIER)
        if request_tokens > JEV_REQUEST_TOKEN_BUDGET or evaluation_tokens > JEV_EVALUATION_TOKEN_BUDGET:
            raise ValueError(f'jev_request_exceeds_budget:{request_tokens}:{evaluation_tokens}')
        body = self._post(payload)
        if not isinstance(body, Mapping) or not isinstance(body.get('answers'), Mapping):
            raise JevCallError('jev_response_answers_missing')
        answers = body['answers']
        for name in questions:
            _probability(answers.get(name), name)
        usage = body.get('usage') or {}
        if not isinstance(usage, Mapping):
            raise JevCallError('jev_response_usage_invalid')
        return JevResponse(model=str(body.get('model') or self.model),
                           answers={str(name): dict(answer) for name, answer in answers.items()
                                    if isinstance(answer, Mapping)},
                           input_tokens=int(usage.get('input_tokens') or 0),
                           output_tokens=int(usage.get('output_tokens') or 0), attempts=1)

    async def nouls(self, *, state, questions):
        """Several named Noul probabilities from one shared state (one request, run off the event loop)."""
        typed = self._noul_questions(questions)
        response = await asyncio.to_thread(self.evaluate, state=state, questions=typed)
        return JevNoulVectorDecision(probabilities={name: _probability(response.answers.get(name), name)
                                                    for name in typed}, response=response)


__all__ = ['JEV_API_ENDPOINT', 'JEV_EVALUATION_TOKEN_BUDGET', 'JEV_KEY_FILE', 'JEV_KEY_VARIABLE', 'JEV_MODEL',
           'JEV_REQUEST_TOKEN_BUDGET', 'JEV_TOKEN_BOUND', 'JEV_TOKEN_HEADROOM', 'JevCallError', 'JevDecisionClient',
           'jev_token_estimate', 'token_bound', 'window_text']
