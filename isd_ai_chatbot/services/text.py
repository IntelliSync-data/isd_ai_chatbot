# -*- coding: utf-8 -*-
"""Plain-Python text helpers. Nothing here touches the ORM, so it can be
tested on its own."""
import re
import unicodedata

STOP_WORDS = {
    'la', 'va', 'cua', 'cac', 'cho', 'trong', 'khi', 'nhu', 'the', 'nao',
    'voi', 'mot', 'nhung', 'duoc', 'can', 'co', 'de', 'tai', 've', 'tu',
    'toi', 'minh', 'ban', 'em', 'anh', 'chi', 'oi', 'a', 'ah', 'nhe', 'nha',
    'and', 'for', 'with', 'how', 'what', 'is', 'are', 'to', 'in', 'of', 'an',
    'it', 'i', 'my', 'me', 'you', 'your', 'do', 'does', 'can', 'please',
}

EN_SIGNAL_WORDS = {
    'what', 'how', 'why', 'where', 'when', 'who', 'which', 'can', 'could',
    'would', 'should', 'does', 'do', 'is', 'are', 'price', 'cost', 'buy',
    'order', 'much', 'hello', 'hi', 'hey', 'help', 'please', 'thanks',
    'thank', 'schedule', 'warranty', 'return', 'refund', 'shipping',
    'delivery', 'contact', 'want', 'need', 'would', 'like', 'my', 'name',
}

VI_SIGNAL_WORDS = {
    'gia', 'bao', 'nhieu', 'mua', 'dat', 'cho', 'khong', 'co', 'duoc', 'sao',
    'the', 'nao', 'chao', 'ad', 'shop', 'hanh', 'doi', 'tra', 'ship', 'uu',
    'dai', 'minh', 'toi', 'ban', 'em', 'anh', 'chi', 'can', 'muon', 'tu', 'van',
}

_VI_ACCENTS = re.compile(
    r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]')

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE_RE = re.compile(r'(?:\+?\d[\d\s.-]{6,14}\d)')
SESSION_RE = re.compile(r'^[A-Za-z0-9:_\-]{1,100}$')


def normalize(text):
    """Lowercase, strip Vietnamese accents and punctuation: 'Giá?' -> 'gia'."""
    if not text:
        return ''
    s = text.lower().replace('đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = re.sub(r'[̀-ͯ]', '', s)
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def detect_language(text, hint=''):
    """'vi' or 'en'. An accented letter settles it; otherwise count signal words."""
    hint = (hint or '').lower()[:2]
    if not text:
        return 'en' if hint == 'en' else 'vi'
    if _VI_ACCENTS.search(text.lower()):
        return 'vi'
    words = re.findall(r'[a-z]+', text.lower())
    en_hits = sum(1 for w in words if w in EN_SIGNAL_WORDS)
    vi_hits = sum(1 for w in words if w in VI_SIGNAL_WORDS)
    if en_hits > vi_hits:
        return 'en'
    if vi_hits > en_hits:
        return 'vi'
    return hint if hint in ('en', 'vi') else 'vi'


def tokens(norm_text):
    return [t for t in norm_text.split(' ') if len(t) >= 2 and t not in STOP_WORDS]


def parse_expansions(raw):
    """Parse the query-expansion table typed into Settings.

    One rule per line, triggers on the left and the words to add on the right:

        price, cost, how much => gia ban uu dai

    It is what lets a question asked in English find a document written in
    Vietnamese, without a translation service. Lines without '=>' are ignored.
    """
    rules = []
    for line in (raw or '').splitlines():
        if '=>' not in line:
            continue
        left, right = line.split('=>', 1)
        triggers = [normalize(t) for t in left.split(',') if normalize(t)]
        extra = normalize(right)
        if triggers and extra:
            pattern = re.compile(r'\b(?:%s)\b' % '|'.join(re.escape(t) for t in triggers))
            rules.append((pattern, extra))
    return rules


def expand_query(norm_q, rules):
    extra = [add for pattern, add in rules if pattern.search(norm_q)]
    return (norm_q + ' ' + ' '.join(extra)).strip()


def clean_phone(raw):
    digits = re.sub(r'\D', '', raw or '')
    return raw.strip() if 8 <= len(digits) <= 15 else ''


def valid_email(email):
    email = (email or '').strip().lower()
    if len(email) > 254 or not re.fullmatch(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', email):
        return ''
    return email


def valid_session_id(session_id):
    session_id = (session_id or '').strip()
    return session_id if SESSION_RE.match(session_id) else ''
