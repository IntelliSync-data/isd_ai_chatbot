# -*- coding: utf-8 -*-
"""Pull contact details out of free text, without an NLP library.

isd_chatbot leaned on spaCy for this, and its name-extraction branch crashed
on the very case it was built for (a recognised name), throwing away the email
and phone it had already found. Regex is less clever and far more predictable,
and it needs nothing installed.
"""
import re

from .text import EMAIL_RE, PHONE_RE, clean_phone, detect_language, normalize

# Compared without accents, so "gap nhan vien" counts as "gặp nhân viên"
HANDOFF_PHRASES = (
    'noi chuyen voi nguoi that', 'gap nguoi that', 'gap nhan vien',
    'gap tu van vien', 'nhan vien tu van', 'tu van vien', 'nguoi that',
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
# The same for a message typed without any accent. Words that lose their
# meaning without accents are left out: "luc" is lúc and also the name Lực,
# "gia" is giá and also Gia, "toi" is tối and also tôi.
_TOPIC_PLAIN_RE = re.compile(
    r'\b(tu van|dai ly|san pham|khoa hoc|lo trinh|van de|ho tro|can|muon|bao gia|hop tac|dau tu|hoc phi)\b')
_TIME_PLAIN_RE = re.compile(r'\b(chieu|ngay mai|hom nay|buoi)\b')


def _has_accents(text):
    return bool(re.search(r'[À-ỹđĐ]', text or ''))


def _topic_word(seg):
    return bool(_TOPIC_RE.search(seg)) or (not _has_accents(seg) and bool(_TOPIC_PLAIN_RE.search(normalize(seg))))


def _time_word(seg):
    return bool(_TIME_RE.search(seg)) or (not _has_accents(seg) and bool(_TIME_PLAIN_RE.search(normalize(seg))))


def _title_cased(seg):
    words = [w for w in seg.split() if w]
    return bool(words) and all(w[0].isupper() for w in words)
_SKIP_EXTRA_RE = re.compile(
    r'\b(cứ gọi|gọi luôn|không có|lúc nào cũng được|sao cũng được|gọi giờ nào cũng được|'
    r'tư vấn chung|anytime|any time|whenever)\b',
    flags=re.I,
)
# Matched without accents. A bare "không" to "what would you like to discuss?"
# means nothing in particular, and used to leave the bot asking forever.
_SKIP_PLAIN_RE = re.compile(
    r'\b(cu goi|goi luon|khong co gi|luc nao cung duoc|sao cung duoc|gio nao cung duoc|'
    r'tu van chung|bo qua|anytime|any time|whenever|nothing else|thats all|that s all)\b')
_SKIP_WHOLE = {
    'khong', 'khong a', 'khong can', 'ko', 'k', 'khong co', 'thoi', 'chua', 'het roi', 'vay thoi',
    'no', 'nope', 'no thanks', 'skip', 'none',
}
_NAME_INTRO_RE = re.compile(
    # Each Vietnamese phrase twice: many customers type without accents
    r'(?:mình tên là|tên mình là|tôi tên là|mình tên|tên là|mình là|tôi là|em là|anh là|'
    r'chị là|họ tên là|họ tên:?|'
    r'minh ten la|ten minh la|toi ten la|minh ten|ten la|minh la|toi la|em la|anh la|'
    r'chi la|ho ten la|ho ten:?|'
    r'my name is|my name\'s|i am|i\'m|this is|name:)\s*'
    r'([A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,3}?)'
    r'(?=\s*(?:[,;.|\-–—]|cần|muốn|tư vấn|hỏi|liên hệ|gọi|vấn đề|'
    r'can|muon|tu van|hoi|lien he|goi|van de|and|want|need|$))',
    flags=re.I,
)
_QUESTION_START_RE = re.compile(
    r'^(what|how|why|where|when|who|which|could|is|are|does|'
    r'bao nhiêu|giá|tại sao|vì sao|làm sao|như thế nào|có|khi nào|ở đâu)\b',
    flags=re.I,
)
# "can" and "do" are also cần and đó typed without accents ("can tu van..."),
# so they only start a question in a message that reads as English
_QUESTION_START_EN_RE = re.compile(r'^(can|do)\b', flags=re.I)
# Question words matched without accents, anywhere in the message: Vietnamese
# puts them at the end ("học phí bao nhiêu"). "co" is left out: it is có and cô.
_QUESTION_PLAIN_RE = re.compile(
    r'\b(bao nhieu|nhu the nao|the nao|nhu nao|o dau|khi nao|tai sao|vi sao|lam sao|la gi|'
    r'duoc khong|co khong|khong a|bao lau|may gio|gia ca)\b')

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
    # "em là sinh viên" says who someone is, not what they are called
    'sinh vien', 'hoc sinh', 'giao vien', 'phu huynh', 'nhan vien', 'khach hang', 'khach',
    'me be', 'bo be', 'student', 'a student', 'a parent', 'parent', 'teacher',
}


def _is_not_a_name(seg):
    from .text import normalize
    return normalize(seg) in _NOT_A_NAME


def is_handoff_request(text):
    plain = normalize(text)
    return any(p in plain for p in HANDOFF_PHRASES)


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
    plain = normalize(lower)
    if re.search(r'\b(ten|minh la|em la|anh la|chi la|toi la|my name|i am|i m)\b', plain):
        return False
    return (lower.endswith('?') or bool(_QUESTION_START_RE.search(lower))
            or bool(_QUESTION_PLAIN_RE.search(plain))
            or (bool(_QUESTION_START_EN_RE.search(lower)) and detect_language(lower) == 'en'))


def wants_to_skip(text):
    plain = normalize(text)
    return bool(_SKIP_EXTRA_RE.search(text or '')) or plain in _SKIP_WHOLE or bool(_SKIP_PLAIN_RE.search(plain))


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
    if m and m.group(1) and not _topic_word(m.group(1)) and not _is_not_a_name(m.group(1)):
        name = m.group(1).strip()
        rem = rem.replace(m.group(0), ' ').strip()
    elif m:
        # "em là phụ huynh": the customer said who they are, which is not a
        # name, so no other part of the message is taken for one either
        return '', rem

    topic_parts = []
    for seg in (s.strip() for s in re.split(r'[,;|\-–—]+', rem) if s.strip()):
        words = seg.split()
        if (not name and 1 <= len(words) <= 4 and 2 <= len(seg) <= 35
                and not re.search(r'\d', seg)
                and not _topic_word(seg)
                and (not _time_word(seg) or _title_cased(seg))
                and not _SKIP_EXTRA_RE.search(seg)
                and not looks_like_question(seg)
                and not _is_not_a_name(seg)):
            name = re.sub(r'^(anh|chị|em|bạn|mr|ms|mrs)\.?\s+', '', seg, flags=re.I).strip() or seg
        elif _is_not_a_name(seg):
            continue
        elif len(words) >= 2 or _topic_word(seg) or _time_word(seg) or _SKIP_EXTRA_RE.search(seg):
            topic_parts.append(seg)
    return name, ', '.join(topic_parts).strip()
