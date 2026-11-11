# -*- coding: utf-8 -*-
"""Pull contact details out of free text, without an NLP library.

isd_chatbot leaned on spaCy for this, and its name-extraction branch crashed
on the very case it was built for (a recognised name), throwing away the email
and phone it had already found. Regex is less clever and far more predictable,
and it needs nothing installed.
"""
import re

from .text import EMAIL_RE, PHONE_RE, clean_phone

HANDOFF_PHRASES = (
    'nói chuyện với người thật', 'gặp người thật', 'gặp nhân viên',
    'gặp tư vấn viên', 'nhân viên tư vấn', 'tư vấn viên', 'người thật',
    'talk to a human', 'real person', 'human agent', 'speak to someone',
    'talk to someone', 'live agent',
)

# Words that make a phrase a topic, never a name
_TOPIC_RE = re.compile(
    r'\b(tư vấn|đại lý|mua|sản phẩm|khoá học|khóa học|lộ trình|vấn đề|hỗ trợ|cần|muốn|'
    r'báo giá|sỉ|hợp tác|đầu tư|giờ|lúc|buổi|'
    r'consult|price|quote|buy|order|support|help|need|want|meeting|call)\b',
    flags=re.I,
)
# Words that are usually about time but are also common Vietnamese names:
# "mai" is tomorrow and it is Mai; "sáng" is morning and it is Sáng
_TIME_RE = re.compile(r'\b(sáng|chiều|tối|mai|nay|tomorrow|today|morning|afternoon|evening)\b', flags=re.I)
_TOPIC_OR_TIME_RE = re.compile('%s|%s' % (_TOPIC_RE.pattern, _TIME_RE.pattern), flags=re.I)


def _title_cased(seg):
    words = [w for w in seg.split() if w]
    return bool(words) and all(w[0].isupper() for w in words)
_SKIP_EXTRA_RE = re.compile(
    r'\b(cứ gọi|gọi luôn|không có|lúc nào cũng được|sao cũng được|gọi giờ nào cũng được|'
    r'tư vấn chung|anytime|any time|whenever)\b',
    flags=re.I,
)
_NAME_INTRO_RE = re.compile(
    r'(?:mình tên là|tên mình là|tôi tên là|mình tên|tên là|mình là|tôi là|em là|anh là|'
    r'chị là|họ tên là|họ tên:?|my name is|my name\'s|i am|i\'m|this is|name:)\s*'
    r'([A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,3}?)'
    r'(?=\s*(?:[,;.|\-–—]|cần|muốn|tư vấn|hỏi|liên hệ|gọi|vấn đề|and|want|need|$))',
    flags=re.I,
)
_QUESTION_START_RE = re.compile(
    r'^(what|how|why|where|when|who|which|can|could|is|are|do|does|'
    r'bao nhiêu|giá|tại sao|vì sao|làm sao|như thế nào|có|khi nào|ở đâu)\b',
    flags=re.I,
)

# Dates as people type them in Vietnamese and English: 25/06/2026, 25-06-2026,
# optionally followed by a time (14h, 14:30, lúc 9 giờ, at 9h).
_DATE_RE = re.compile(
    r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})'
    r'(?:[\s,]+(?:lúc|at|vào)?\s*(\d{1,2})\s*(?:[:h](\d{2})?|giờ|gio|gi[oơờ]))?',
    flags=re.I,
)


# Short replies that are never a name, however name-shaped they look
_NOT_A_NAME = {
    'ok', 'okay', 'oke', 'ok a', 'vang', 'da', 'u', 'uh', 'um', 'yes', 'no', 'co',
    'khong', 'cam on', 'thanks', 'thank you', 'chao', 'hi', 'hello', 'hey', 'roi',
    'duoc', 'dung', 'sai', 'xin chao', 'chao ban', 'alo', 'test',
}


def _is_not_a_name(seg):
    from .text import normalize
    return normalize(seg) in _NOT_A_NAME


def is_handoff_request(text):
    lower = (text or '').lower()
    return any(p in lower for p in HANDOFF_PHRASES)


def find_email(text):
    m = EMAIL_RE.search(text or '')
    return m.group(0).strip() if m else ''


def find_phone(text):
    for m in PHONE_RE.finditer(text or ''):
        phone = clean_phone(m.group(0))
        if phone:
            return phone
    return ''


def find_datetime(text):
    """A local 'YYYY-MM-DD HH:MM:00' string, 09:00 when only a day is given."""
    m = _DATE_RE.search(text or '')
    if not m:
        return ''
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hour = int(m.group(4)) if m.group(4) else 9
    minute = int(m.group(5)) if m.group(5) else 0
    if not (1 <= day <= 31 and 1 <= month <= 12 and 0 <= hour <= 23 and 0 <= minute <= 59):
        return ''
    return '%04d-%02d-%02d %02d:%02d:00' % (year, month, day, hour, minute)


def looks_like_question(text):
    """Someone asking about the product in the middle of leaving their details."""
    lower = (text or '').lower().strip()
    if find_email(lower) or find_phone(lower):
        return False
    if re.search(r'\b(tên|mình là|em là|anh là|chị là|my name|i am|i\'m)\b', lower):
        return False
    return lower.endswith('?') or bool(_QUESTION_START_RE.search(lower))


def wants_to_skip(text):
    return bool(_SKIP_EXTRA_RE.search(text or ''))


def extract_name_and_topic(msg):
    """Split one message into (name, topic), after removing phone and email."""
    rem = PHONE_RE.sub(' ', msg or '')
    rem = EMAIL_RE.sub(' ', rem)
    rem = re.sub(r'\b(sdt|sđt|số điện thoại|phone|tel|email|mail)\s*:?', ' ', rem, flags=re.I)
    rem = re.sub(r'\s+', ' ', rem).strip()
    if not rem:
        return '', ''

    name = ''
    m = _NAME_INTRO_RE.search(rem)
    if m and m.group(1) and not _TOPIC_RE.search(m.group(1)) and not _is_not_a_name(m.group(1)):
        name = m.group(1).strip()
        rem = rem.replace(m.group(0), ' ').strip()

    topic_parts = []
    for seg in (s.strip() for s in re.split(r'[,;|\-–—]+', rem) if s.strip()):
        words = seg.split()
        if (not name and 1 <= len(words) <= 4 and 2 <= len(seg) <= 35
                and not re.search(r'\d', seg)
                and not _TOPIC_RE.search(seg)
                and (not _TIME_RE.search(seg) or _title_cased(seg))
                and not _SKIP_EXTRA_RE.search(seg)
                and not looks_like_question(seg)
                and not _is_not_a_name(seg)):
            name = re.sub(r'^(anh|chị|em|bạn|mr|ms|mrs)\.?\s+', '', seg, flags=re.I).strip() or seg
        elif _is_not_a_name(seg):
            continue
        elif len(words) >= 2 or _TOPIC_OR_TIME_RE.search(seg) or _SKIP_EXTRA_RE.search(seg):
            topic_parts.append(seg)
    return name, ', '.join(topic_parts).strip()
