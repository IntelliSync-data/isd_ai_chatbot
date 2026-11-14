# -*- coding: utf-8 -*-
"""Read a web page into knowledge-base text.

The page's headings become '## ' lines, because the search splits documents
there and the bot quotes the section an answer came from.
"""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from lxml import html as lxml_html

TIMEOUT = 15
MAX_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 5
USER_AGENT = 'Mozilla/5.0 (compatible; ISD-AI-Chatbot/1.0; +https://intellisyncdata.com)'

# Never text: code, styling, and the site menu that repeats on every page
DROP_TAGS = ('script', 'style', 'noscript', 'template', 'svg', 'iframe', 'nav', 'form', 'button', 'select')
HEADING_TAGS = ('h1', 'h2', 'h3')
BLOCK_TAGS = ('p', 'div', 'section', 'article', 'main', 'header', 'footer', 'aside', 'li', 'ul', 'ol',
              'table', 'tr', 'dt', 'dd', 'dl', 'blockquote', 'pre', 'address', 'figcaption',
              'h4', 'h5', 'h6', 'br', 'hr')


class FetchError(Exception):
    """code: what went wrong, for the caller to put into words; params fill them in."""

    def __init__(self, code, **params):
        super().__init__(code)
        self.code = code
        self.params = params


def _check_public(url):
    """Refuse anything but a public http(s) address.

    The server makes the request, so without this a link to localhost, the
    office network or the cloud metadata address would let anyone who edits
    the knowledge base read services that are not meant to be reachable.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise FetchError('scheme')
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
    except socket.gaierror:
        raise FetchError('dns', host=parsed.hostname)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise FetchError('internal', host=parsed.hostname)


def fetch(url):
    """(final url, html bytes, charset or None), following redirects one hop at a time
    so each hop is checked."""
    url = (url or '').strip()
    for _hop in range(MAX_REDIRECTS + 1):
        _check_public(url)
        try:
            resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True,
                                headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'})
        except requests.RequestException as exc:
            raise FetchError('unreachable', error=exc.__class__.__name__)
        if resp.is_redirect:
            url = urljoin(url, resp.headers.get('Location', ''))
            resp.close()
            continue
        if resp.status_code >= 400:
            raise FetchError('http', status=resp.status_code)
        ctype = resp.headers.get('Content-Type', '')
        if 'html' not in ctype and 'text/plain' not in ctype:
            raise FetchError('not_html', type=ctype.split(';')[0] or '?')
        body = b''
        for chunk in resp.iter_content(64 * 1024):
            body += chunk
            if len(body) > MAX_BYTES:
                raise FetchError('too_big')
        charset = re.search(r'charset=([\w-]+)', ctype, re.I)
        return url, body, charset.group(1) if charset else None
    raise FetchError('redirects')


def html_to_text(body, charset=None):
    """(page title, text with '## ' headings)."""
    parser = lxml_html.HTMLParser(encoding=charset) if charset else None
    try:
        doc = lxml_html.document_fromstring(body, parser=parser)
    except Exception:
        raise FetchError('unreadable')
    title = (doc.findtext('.//title') or '').strip()
    for el in doc.xpath('//comment()'):
        el.drop_tree()
    for tag in DROP_TAGS:
        for el in doc.iter(tag):
            el.drop_tree()

    # Mark where lines break, then read the whole page at once: text sitting
    # directly in a <div> is kept, which walking <p> tags alone would miss.
    # Line breaks in the HTML source are only formatting, so they go first.
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        el.text = re.sub(r'\s+', ' ', el.text) if el.text else el.text
        el.tail = re.sub(r'\s+', ' ', el.tail) if el.tail else el.tail
        if el.tag == 'br' and any(a.tag in HEADING_TAGS for a in el.iterancestors()):
            # A heading wrapped onto two lines for layout is still one heading
            el.tail = ' ' + (el.tail or '')
        elif el.tag in HEADING_TAGS:
            el.text = '\n\n## ' + (el.text or '').lstrip()
            el.tail = '\n' + (el.tail or '')
        elif el.tag in BLOCK_TAGS:
            el.text = '\n' + (el.text or '')
            el.tail = '\n' + (el.tail or '')
        elif el.tag in ('td', 'th'):
            el.tail = ' | ' + (el.tail or '')

    body_el = doc.find('body')
    raw = (body_el if body_el is not None else doc).text_content()
    lines, seen = [], set()
    for line in raw.split('\n'):
        line = re.sub(r'\s+', ' ', line).strip().rstrip('|').strip()
        if line in ('##', '## '):
            continue
        # The same banner or slogan often appears several times on one page
        key = line.lower()
        if not line or (key in seen and not line.startswith('## ')):
            continue
        seen.add(key)
        lines.append(line)
    text = '\n'.join(lines)
    text = re.sub(r'\n(## )', r'\n\n\1', text).strip()
    return title, text


def read_page(url):
    """(final url, page title, text). Raises FetchError."""
    final_url, body, charset = fetch(url)
    title, text = html_to_text(body, charset)
    if len(text) < 80:
        raise FetchError('no_text')
    return final_url, title, text
