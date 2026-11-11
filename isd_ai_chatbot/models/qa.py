# -*- coding: utf-8 -*-
from odoo import fields, models


class IsdAiChatbotQa(models.Model):
    """An approved answer, given word for word when its keywords match.

    Takes over two things: isd_chatbot's Q&A rows, and the replies
    chatbot_ai_rag had written into its Python code. With a language model
    configured, the matching answer is handed to it as the authority, so the
    price it quotes is the price typed here.
    """
    _name = 'isd.ai.chatbot.qa'
    _description = 'AI Chatbot Q&A'
    _order = 'sequence, id'

    name = fields.Char(string='Topic', required=True)
    sequence = fields.Integer(default=10, help='When two entries match equally, the lower one wins')
    active = fields.Boolean(default=True)
    keywords = fields.Text(
        required=True,
        help='One keyword or phrase per line, in any language. Accents and case do not matter. '
             'The longest phrase found in the question decides which entry answers.')
    answer_vi = fields.Text(string='Answer (VI)')
    answer_en = fields.Text(string='Answer (EN)')
    show_lead_form = fields.Boolean(
        string='Offer the Contact Form',
        help='On the website, open the name/phone/email form under this answer')
    hit_count = fields.Integer(string='Times Used', readonly=True, copy=False)

    def _answer_for(self, lang):
        self.ensure_one()
        primary, other = (self.answer_en, self.answer_vi) if lang == 'en' else (self.answer_vi, self.answer_en)
        return (primary or other or '').strip()
