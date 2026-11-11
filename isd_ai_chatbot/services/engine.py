# -*- coding: utf-8 -*-
"""One conversation turn: the same for the website widget, Zalo and Messenger.

The lead flow keeps its state on the conversation record. chatbot_ai_rag kept
it in the browser and worked it out again each turn by searching the history
the browser sent for its own previous replies; that broke on a page reload,
trusted whatever the browser claimed, and could not work at all for Zalo or
Messenger, which send no history.
"""
import re

from .text import detect_language, parse_expansions
from .lead_extract import (
    is_handoff_request, find_email, find_phone, find_datetime,
    looks_like_question, wants_to_skip, extract_name_and_topic,
)
from .retrieval import search_knowledge, match_qa
from .llm import generate

_GREETING_RE = re.compile(
    r'^(xin chào|chào|chao|alo|hi|hello|hey|shop ơi|ad ơi|ơi|good (morning|afternoon|evening))[\s!.,?]*$',
    re.I)
_PARTIAL_PHONE_RE = re.compile(r'^\+?[\d\s.-]{3,7}$')

# Conversation scaffolding only. Anything that is a fact about the business -
# prices, hotlines, policies - lives in Q&A and the knowledge base, never here.
T = {
    'vi': {
        'handoff': (
            "Dạ được ạ! Để kết nối đúng người hỗ trợ, bạn cho mình biết bạn muốn trao đổi về vấn đề gì nhé.\n\n"
            "Mình sẽ ghi nhận và chuyển cho đội ngũ hỗ trợ liên hệ lại. Bạn cho mình xin:\n"
            "* **Họ tên**, **số điện thoại** và **email**\n"
            "* **Thời gian mong muốn được liên hệ** (nếu có)"),
        'bad_phone': ("Dạ số điện thoại vừa nhập có vẻ chưa đủ số ạ. Bạn kiểm tra giúp mình và gửi lại "
                      "**số điện thoại hợp lệ (8–15 chữ số)** hoặc **email** nhé!"),
        'done': ("Dạ cảm ơn **{name}**! ✅ Mình đã ghi nhận đầy đủ thông tin:\n"
                 "* **Họ tên:** {name}\n* **Liên hệ:** {contact}\n* **Nội dung:** {topic}\n\n"
                 "Đội ngũ hỗ trợ sẽ liên hệ lại với bạn sớm nhất. Trong lúc chờ, bạn cần mình giải đáp thêm gì không ạ?"),
        'noted': "Dạ mình đã ghi nhận {noted} của bạn rồi ạ! 📝",
        'ask': "Để chuyên viên hỗ trợ đúng người, bạn cho mình xin thêm:",
        'need_name': "* **Họ tên** của bạn",
        'need_contact': "* **Số điện thoại** và/hoặc **email**",
        'need_topic': "* **Vấn đề bạn muốn trao đổi** và **thời gian mong muốn được liên hệ**",
        'need_email': " (kèm **email** nếu có)",
        'name_word': 'họ tên', 'contact_word': 'liên hệ', 'topic_word': 'nội dung', 'and': ' và ',
        'you': 'bạn', 'general_topic': 'Trao đổi trực tiếp với chuyên viên',
        'cited': "Dạ theo tài liệu của chúng tôi {cite}:\n\n* **{heading}:** {snippet}\n\nBạn cần mình tư vấn thêm gì không ạ?",
        'more': "Bạn có thể hỏi mình về:",
    },
    'en': {
        'handoff': (
            "Certainly! To connect you with the right person, could you tell me what you'd like to discuss?\n\n"
            "I'll pass your details to our team so they can reach you. Please share:\n"
            "* Your **full name**, **phone number** and **email**\n"
            "* Your **preferred time to be contacted** (if any)"),
        'bad_phone': ("The phone number looks incomplete. Could you check it and send a valid "
                      "**phone number (8–15 digits)** or your **email**?"),
        'done': ("Thank you, **{name}**! ✅ I've recorded your details:\n"
                 "* **Name:** {name}\n* **Contact:** {contact}\n* **Topic:** {topic}\n\n"
                 "Our team will get back to you shortly. Anything else I can help with in the meantime?"),
        'noted': "Thank you! 📝 I've noted your {noted}.",
        'ask': "To get you to the right person, could you also share:",
        'need_name': "* Your **full name**",
        'need_contact': "* Your **phone number** and/or **email**",
        'need_topic': "* **What you'd like to discuss** and **when you'd like to be contacted**",
        'need_email': " (and your **email** if you have one)",
        'name_word': 'name', 'contact_word': 'contact', 'topic_word': 'topic', 'and': ' and ',
        'you': 'there', 'general_topic': 'A direct conversation with our team',
        'cited': "According to our documents {cite}:\n\n* **{heading}:** {snippet}\n\nIs there anything else I can help with?",
        'more': "You can ask me about:",
    },
}


class ChatEngine:

    def __init__(self, env):
        self.env = env
        self.config = env['isd.ai.chatbot.config'].sudo().get_config()

    # ------------------------------------------------------------------ entry
    def reply(self, conversation, text, lang_hint='', external_message_id=False):
        """Answer one message and record both sides. Returns a dict for the caller."""
        lang = detect_language(text, lang_hint or conversation.lang)
        if conversation.lang != lang:
            conversation.lang = lang
        conversation._log_message('user', text, external_message_id=external_message_id)

        result = self._lead_flow(conversation, text, lang) or self._answer(conversation, text, lang)
        result.setdefault('lang', lang)
        conversation._log_message(
            'bot', result['reply'], provider=result.get('provider'),
            qa_id=result.get('qa_id'), citation_count=len(result.get('citations') or []))
        return result

    # -------------------------------------------------------------- lead flow
    def _lead_flow(self, conv, text, lang):
        t = T[lang]
        if is_handoff_request(text):
            conv.lead_state = 'collecting'
            return {'reply': t['handoff'], 'provider': 'lead', 'show_lead_form': True}

        phone, email = find_phone(text), find_email(text)
        collecting = conv.lead_state == 'collecting'
        if not collecting and not (phone or email):
            return None
        # A product question asked halfway through: answer it, keep collecting
        if collecting and not (phone or email) and looks_like_question(text):
            return None
        if _PARTIAL_PHONE_RE.match(text.strip()):
            return {'reply': t['bad_phone'], 'provider': 'lead'}

        name, topic = extract_name_and_topic(text)
        vals = {'lead_state': 'collecting'}
        if phone:
            vals['lead_phone'] = phone
        if email:
            vals['lead_email'] = email
        if name and not conv.lead_name:
            vals['lead_name'] = name[:100]
        if topic:
            known = [p for p in (conv.lead_topic or '').split(' | ') if p]
            if topic not in known:
                vals['lead_topic'] = ' | '.join(known + [topic])[:500]
        when = find_datetime(text)
        if when:
            vals['lead_datetime'] = when
        conv.write(vals)

        has_contact = bool(conv.lead_phone or conv.lead_email)
        if has_contact:
            conv._upsert_lead()

        contact = ' / '.join(x for x in (conv.lead_phone, conv.lead_email) if x)
        if has_contact and ((conv.lead_name and conv.lead_topic) or wants_to_skip(text)):
            conv.lead_state = 'done'
            return {
                'reply': t['done'].format(name=conv.lead_name or t['you'], contact=contact,
                                          topic=conv.lead_topic or t['general_topic']),
                'provider': 'lead', 'lead_captured': True,
            }

        noted = []
        if conv.lead_name:
            noted.append('%s (**%s**)' % (t['name_word'], conv.lead_name))
        if has_contact:
            noted.append('%s (**%s**)' % (t['contact_word'], contact))
        if conv.lead_topic:
            noted.append('%s (**%s**)' % (t['topic_word'], conv.lead_topic))
        missing = []
        if not conv.lead_name:
            missing.append(t['need_name'] + ('' if conv.lead_email else t['need_email']))
        if not has_contact:
            missing.append(t['need_contact'])
        if not conv.lead_topic:
            missing.append(t['need_topic'])
        parts = [t['noted'].format(noted=t['and'].join(noted))] if noted else []
        parts.append(t['ask'] + '\n' + '\n'.join(missing))
        return {'reply': '\n\n'.join(parts), 'provider': 'lead'}

    # ----------------------------------------------------------------- answer
    def _answer(self, conv, text, lang):
        cfg = self.config
        qa = match_qa(self.env, text)
        qa_answer = qa._answer_for(lang) if qa else ''
        if qa:
            # One statement, so two chats hitting the same answer at once
            # cannot lose a count the way a read-then-write would
            self.env.cr.execute(
                'UPDATE isd_ai_chatbot_qa SET hit_count = COALESCE(hit_count, 0) + 1 WHERE id = %s', (qa.id,))
        citations = search_knowledge(self.env, text, parse_expansions(cfg.query_expansions), top_k=3)

        reply, provider = '', ''
        if cfg.has_language_model:
            reply, provider = generate(
                cfg, self._system_prompt(lang, qa_answer, citations),
                conv._history_for_model(limit=8), text)
        if not reply:
            reply, provider = self._internal_reply(text, lang, qa_answer, citations), 'internal'
        return {
            'reply': reply,
            'citations': citations,
            'provider': provider,
            'qa_id': qa.id if qa else False,
            'show_lead_form': bool(qa and qa.show_lead_form),
        }

    def _system_prompt(self, lang, qa_answer, citations):
        cfg = self.config
        refs = '\n\n'.join(
            '[%s] %s — %s\n%s' % (c['index'], c['title'], c['sectionHeading'], c['snippet'])
            for c in citations) or '(none)'
        if lang == 'en':
            lang_rule = 'The customer writes in English: reply in English only.'
        else:
            lang_rule = 'The customer writes in Vietnamese: reply in Vietnamese only, addressing them as: %s.' % (
                cfg.pronoun_style or 'bạn')
        lines = [
            'You are the customer-support assistant of %s%s.' % (
                cfg.business_name or self.env.company.name,
                (' (%s)' % cfg.business_website) if cfg.business_website else ''),
            lang_rule,
            'Tone and length: %s Keep it under about 90 words.' % (cfg.tone_instruction or 'Warm, clear, concise.'),
        ]
        if cfg.core_philosophy:
            lines.append('What matters to us: %s' % cfg.core_philosophy)
        if cfg.forbidden_claims:
            lines.append('Never say: %s' % cfg.forbidden_claims)
        if cfg.handoff_rule:
            lines.append('When to hand over to a person: %s' % cfg.handoff_rule)
        lines.append('Answer only from the material below. If it does not cover the question, say so and '
                     'offer to connect the customer with our team. Never invent prices, dates, contact '
                     'details or policies. Mark the references you use as [1], [2].')
        if qa_answer:
            lines.append('APPROVED ANSWER (use it; it overrides the documents):\n%s' % qa_answer)
        lines.append('REFERENCES:\n%s' % refs)
        return '\n'.join(lines)

    def _internal_reply(self, text, lang, qa_answer, citations):
        """The answer when no language model is configured or none responded."""
        cfg, t = self.config, T[lang]
        if _GREETING_RE.match(text.strip()):
            welcome = cfg._text('welcome_message', lang)
            topics = cfg._suggested_questions(lang)[:3]
            if topics:
                welcome += '\n\n%s\n%s' % (t['more'], '\n'.join('* %s' % q for q in topics))
            return welcome
        if qa_answer:
            return qa_answer
        if citations:
            first = citations[0]
            snippet = first['snippet'][:220] + ('...' if len(first['snippet']) > 220 else '')
            return t['cited'].format(cite='[1]', heading=first['sectionHeading'], snippet=snippet)
        return cfg._text('fallback_message', lang)
