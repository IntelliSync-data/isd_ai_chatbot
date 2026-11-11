# -*- coding: utf-8 -*-
"""Calls to the language models. Every failure returns '' so the caller can
fall back, because a chat that dies on a timeout is worse than one that
answers from its own documents."""
import json
import logging
import re

import requests

from . import lead_extract

_logger = logging.getLogger(__name__)

TIMEOUT = 15


def _gemini(api_key, model, system_prompt, history, user_text, max_tokens=400, temperature=0.25):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % (
        model or 'gemini-2.5-flash')
    contents = [{'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [{'text': m['content']}]}
                for m in history]
    contents.append({'role': 'user', 'parts': [{'text': user_text}]})
    payload = {
        'system_instruction': {'parts': [{'text': system_prompt}]},
        'contents': contents,
        'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens},
    }
    # The key goes in a header, not the query string, so it stays out of
    # proxy and access logs
    resp = requests.post(url, json=payload, timeout=TIMEOUT,
                         headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key})
    resp.raise_for_status()
    data = resp.json()
    return (data.get('candidates') or [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '') or ''


def _openai(api_key, model, system_prompt, history, user_text, max_tokens=400, temperature=0.25):
    messages = [{'role': 'system', 'content': system_prompt}]
    messages += [{'role': m['role'], 'content': m['content']} for m in history]
    messages.append({'role': 'user', 'content': user_text})
    resp = requests.post(
        'https://api.openai.com/v1/chat/completions', timeout=TIMEOUT,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % api_key},
        json={'model': model or 'gpt-4o-mini', 'temperature': temperature,
              'max_tokens': max_tokens, 'messages': messages})
    resp.raise_for_status()
    data = resp.json()
    return (data.get('choices') or [{}])[0].get('message', {}).get('content', '') or ''


def generate(config, system_prompt, history, user_text, max_tokens=400, temperature=0.25):
    """(reply, provider label). Gemini first, then OpenAI, then ('', '')."""
    attempts = []
    if (config.gemini_api_key or '').strip():
        attempts.append(('Gemini', _gemini, config.gemini_api_key.strip(), config.gemini_model))
    if (config.openai_api_key or '').strip():
        attempts.append(('OpenAI', _openai, config.openai_api_key.strip(), config.openai_model))
    for label, fn, key, model in attempts:
        try:
            reply = fn(key, model, system_prompt, history, user_text, max_tokens, temperature)
            if reply.strip():
                return reply.strip(), label
        except Exception as e:  # network, quota, bad key: try the next one
            _logger.warning("isd_ai_chatbot: %s call failed: %s", label, e)
    return '', ''


EXTRACT_PROMPT = """You extract contact details from a customer's chat message.
The message may be in Vietnamese or English.
Return ONLY a JSON object with these keys, using null for anything not stated:
  "name", "email", "phone", "datetime"
"datetime" is the consultation time the customer asked for, as "YYYY-MM-DD HH:MM".
Do not guess. Do not add any text outside the JSON."""


def extract_contact(config, message):
    """(data dict, log lines). Used by the Analyze button on a lead."""
    log = []
    reply, provider = generate(config, EXTRACT_PROMPT, [], message, max_tokens=300, temperature=0.0)
    if not reply:
        log.append('No language model answered, so the rules were used instead.')
        return _extract_by_rules(message, log)
    log.append('Analyzed with %s.' % provider)
    match = re.search(r'\{.*\}', reply, re.S)
    if not match:
        log.append('The model did not return JSON: %s' % reply[:300])
        return {}, log
    try:
        data = json.loads(match.group(0))
    except ValueError:
        log.append('The model returned invalid JSON: %s' % match.group(0)[:300])
        return {}, log
    clean = {k: (str(data.get(k)).strip() if data.get(k) not in (None, '', 'null') else '')
             for k in ('name', 'email', 'phone', 'datetime')}
    log.append('Found: %s' % ', '.join('%s=%s' % (k, v) for k, v in clean.items() if v) or 'nothing')
    return clean, log


def _has_contact(line):
    return lead_extract.find_email(line) or lead_extract.find_phone(line)


def _extract_by_rules(message, log):
    """The same fields, found by the patterns the chat itself uses, one line at a time."""
    data = {}
    for line in (message or '').splitlines():
        data.setdefault('email', lead_extract.find_email(line))
        data.setdefault('phone', lead_extract.find_phone(line))
        when = lead_extract.find_datetime(line)
        if when:
            data.setdefault('datetime', when[:16])
        # Across a whole transcript a short line is as likely a question as a
        # name, so only lines that introduce someone or carry their contact count
        introduces = lead_extract._NAME_INTRO_RE.search(line) or _has_contact(line)
        name = introduces and lead_extract.extract_name_and_topic(line)[0]
        if name:
            data.setdefault('name', name)
        data = {k: v for k, v in data.items() if v}
    found = ', '.join('%s=%s' % (k, v) for k, v in data.items())
    log.append('Found: %s' % (found or 'nothing'))
    return data, log
