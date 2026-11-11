# -*- coding: utf-8 -*-
"""Find what a question is about: a Q&A answer and/or knowledge passages.

Keyword scoring, not embeddings. It finds the passage that shares the most
words with the question, weighted by where those words appear. A question
phrased with completely different words than the document will miss; the
query-expansion table in Settings is the lever for that.
"""
import re

from .text import normalize, tokens, expand_query

# One parsed copy of the knowledge base per database, rebuilt whenever a
# document is added, removed or edited.
_CHUNK_CACHE = {}
MAX_CHUNK_CHARS = 750


def chunk_document(doc):
    """Split a document on '## ' headings, then long sections on paragraphs."""
    content = (doc.content or '').strip()
    if not content:
        return []
    base = {
        'doc_id': doc.id,
        'title': doc.name,
        'source_type': doc.source_type,
        'file_name': doc.upload_filename or '',
    }
    chunks = []
    for section in re.split(r'\n(?=##+\s)', content):
        section = section.strip()
        if not section:
            continue
        lines = section.split('\n')
        first = re.sub(r'^#+\s*', '', lines[0]).strip()
        is_heading = lines[0].startswith('#')
        heading = first if is_heading or (len(first) <= 90 and len(lines) > 1) else doc.name
        body = '\n'.join(lines[1:]).strip() if is_heading else section

        if len(body) <= MAX_CHUNK_CHARS:
            chunks.append(dict(base, section_heading=heading, content=body or section))
            continue
        buf, part = '', 1
        for para in (p.strip() for p in re.split(r'\n+', body) if p.strip()):
            if buf and len(buf) + len(para) + 1 > MAX_CHUNK_CHARS:
                chunks.append(dict(base, section_heading=heading if part == 1 else '%s (%d)' % (heading, part),
                                   content=buf.strip()))
                buf, part = para, part + 1
            else:
                buf = '%s\n%s' % (buf, para) if buf else para
        if buf.strip():
            chunks.append(dict(base, section_heading=heading if part == 1 else '%s (%d)' % (heading, part),
                               content=buf.strip()))
    return chunks


def _cached_chunks(env):
    docs = env['isd.ai.chatbot.knowledge'].sudo().search([('active', '=', True)])
    signature = '%s:%s' % (len(docs), max((str(d.write_date or '') for d in docs), default=''))
    cached = _CHUNK_CACHE.get(env.cr.dbname)
    if cached and cached['sig'] == signature:
        return cached['chunks']

    all_chunks = []
    for doc in docs:
        for ch in chunk_document(doc):
            ch['norm_head'] = normalize(ch['section_heading'])
            ch['norm_body'] = normalize(ch['content'])
            ch['head_words'] = set(ch['norm_head'].split(' '))
            ch['title_words'] = set(normalize(ch['title']).split(' '))
            ch['body_words'] = set(ch['norm_body'].split(' '))
            all_chunks.append(ch)
    _CHUNK_CACHE[env.cr.dbname] = {'sig': signature, 'chunks': all_chunks}
    return all_chunks


def search_knowledge(env, question, expansion_rules, top_k=3, min_score=1.5):
    """The top passages for a question, as citations the widget can show."""
    norm_q = expand_query(normalize(question), expansion_rules)
    toks = tokens(norm_q)
    if not toks:
        return []
    bigrams = [' '.join(p) for p in zip(toks, toks[1:])]

    scored = []
    for ch in _cached_chunks(env):
        score = 0.0
        for tok in toks:
            if tok in ch['head_words']:
                score += 3.5
            if tok in ch['title_words']:
                score += 2.0
            if tok in ch['body_words']:
                score += 1.5
        # Words appearing together in the order asked are a stronger signal
        # than the same words scattered across a passage
        for bg in bigrams:
            if bg in ch['norm_head']:
                score += 3.0
            elif bg in ch['norm_body']:
                score += 2.0
        if score >= min_score:
            scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)

    citations = []
    for idx, (score, ch) in enumerate(scored[:top_k], start=1):
        snippet = ch['content'][:420] + ('...' if len(ch['content']) > 420 else '')
        citations.append({
            'index': idx,
            'title': ch['title'],
            'sectionHeading': ch['section_heading'],
            'sourceType': ch['source_type'],
            'fileName': ch['file_name'],
            'snippet': snippet,
            'score': round(score, 1),
        })
    return citations


def match_qa(env, question):
    """The Q&A entry whose keywords best cover the question, or an empty record.

    A keyword line matches when all its words appear in the question as a
    phrase. Longer matching phrases win, so 'giao hang mien phi' beats 'giao'.
    """
    norm_q = ' %s ' % normalize(question)
    best, best_score = env['isd.ai.chatbot.qa'], 0
    for qa in env['isd.ai.chatbot.qa'].sudo().search([('active', '=', True)], order='sequence, id'):
        for line in (qa.keywords or '').replace(',', '\n').splitlines():
            phrase = normalize(line)
            if not phrase:
                continue
            if ' %s ' % phrase in norm_q:
                score = len(phrase.split(' '))
                if score > best_score:
                    best, best_score = qa, score
    return best
