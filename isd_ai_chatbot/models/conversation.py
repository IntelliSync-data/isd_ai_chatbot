# -*- coding: utf-8 -*-
from datetime import datetime

import pytz

from odoo import api, fields, models


class IsdAiChatbotConversation(models.Model):
    _name = 'isd.ai.chatbot.conversation'
    _description = 'AI Chatbot Conversation'
    _order = 'last_message_at desc, id desc'
    _rec_name = 'display_label'

    session_id = fields.Char(required=True, index=True,
                             help='Website: a random id kept by the browser. Zalo/Facebook: the channel user id.')
    source_id = fields.Many2one('isd.ai.chatbot.source', string='Source', ondelete='restrict')
    lang = fields.Selection([('vi', 'Vietnamese'), ('en', 'English')], default='vi')
    status = fields.Selection([('active', 'Active'), ('closed', 'Closed')], default='active', index=True)
    user_ip = fields.Char(string='IP Address')
    user_agent = fields.Char()
    page_url = fields.Char(string='Page', help='The page the website widget was opened on')
    message_ids = fields.One2many('isd.ai.chatbot.message', 'conversation_id', string='Messages')
    message_count = fields.Integer(compute='_compute_message_stats', store=True)
    last_message_at = fields.Datetime(compute='_compute_message_stats', store=True)
    display_label = fields.Char(compute='_compute_display_label')

    # Where the contact form sits for this conversation. Kept here, not in the
    # browser, so it survives a reload and works for channels that send no history.
    lead_state = fields.Selection([
        ('idle', 'Not Collecting'), ('collecting', 'Collecting Details'), ('done', 'Details Captured'),
    ], default='idle', string='Contact Flow')
    lead_name = fields.Char(string='Name Given')
    lead_phone = fields.Char(string='Phone Given')
    lead_email = fields.Char(string='Email Given')
    lead_topic = fields.Char(string='Topic Given')
    lead_datetime = fields.Char(string='Time Asked For', help='As typed, in the customer timezone')
    lead_id = fields.Many2one('isd.ai.chatbot.lead', string='Lead', ondelete='set null')

    @api.depends('message_ids', 'message_ids.create_date')
    def _compute_message_stats(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)
            rec.last_message_at = max(rec.message_ids.mapped('create_date'), default=rec.create_date)

    def _compute_display_label(self):
        for rec in self:
            who = rec.lead_name or rec.lead_phone or rec.lead_email or (rec.session_id or '')[:12]
            rec.display_label = '%s · %s' % (rec.source_id.name or '', who) if rec.source_id else who

    # --------------------------------------------------------------- helpers
    @api.model
    def _get_or_create(self, session_id, source_code, **vals):
        """The active conversation for this session, opened if there is none."""
        conv = self.sudo().search([('session_id', '=', session_id), ('status', '=', 'active')],
                                  limit=1, order='id desc')
        if conv:
            return conv
        source = self.env['isd.ai.chatbot.source']._by_code(source_code)
        return self.sudo().create(dict(vals, session_id=session_id, source_id=source.id))

    def _log_message(self, role, content, external_message_id=False, provider=False,
                     qa_id=False, citation_count=0):
        self.ensure_one()
        return self.env['isd.ai.chatbot.message'].sudo().create({
            'conversation_id': self.id,
            'role': role,
            'content': content,
            'external_message_id': external_message_id or False,
            'provider': provider or False,
            'qa_id': qa_id or False,
            'citation_count': citation_count,
        })

    def _history_for_model(self, limit=8):
        """The turns before the current message, oldest first, for the language model."""
        self.ensure_one()
        msgs = self.message_ids.sorted('id')[:-1][-limit:]
        return [{'role': 'assistant' if m.role == 'bot' else 'user', 'content': (m.content or '')[:800]}
                for m in msgs if m.content]

    def _local_datetime_to_utc(self, value):
        tz = pytz.timezone(self.env['isd.ai.chatbot.config'].sudo().get_config().timezone or 'UTC')
        try:
            local = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            return False
        return tz.localize(local).astimezone(pytz.utc).replace(tzinfo=None)

    def _upsert_lead(self):
        """Create this conversation's lead, or bring it up to date."""
        self.ensure_one()
        vals = {
            'name': self.lead_name or self.lead_phone or self.lead_email,
            'phone': self.lead_phone or False,
            'email': self.lead_email or False,
            'topic': self.lead_topic or False,
            'lang': self.lang,
            'message': '\n'.join(m.content for m in self.message_ids.sorted('id')
                                 if m.role == 'user' and m.content)[:4000],
        }
        if self.lead_datetime:
            vals['consultation_datetime'] = self._local_datetime_to_utc(self.lead_datetime)
        Lead = self.env['isd.ai.chatbot.lead'].sudo()
        if self.lead_id:
            lead = self.lead_id
            # Do not overwrite what a salesperson already corrected by hand
            updates = {k: v for k, v in vals.items() if v and (k in ('message', 'topic') or not lead[k])}
            # ...but a name that is only the phone or email standing in for one
            # is a placeholder, and the real name replaces it
            if self.lead_name and lead.name in (lead.phone, lead.email, self.lead_phone, self.lead_email):
                updates['name'] = self.lead_name
            lead.write(updates)
            return lead
        lead = Lead.create(dict(vals, conversation_id=self.id, source_id=self.source_id.id))
        self.lead_id = lead
        return lead


class IsdAiChatbotMessage(models.Model):
    _name = 'isd.ai.chatbot.message'
    _description = 'AI Chatbot Message'
    _order = 'id'

    conversation_id = fields.Many2one('isd.ai.chatbot.conversation', required=True, ondelete='cascade', index=True)
    role = fields.Selection([('user', 'Customer'), ('bot', 'Bot'), ('agent', 'Staff')], required=True)
    content = fields.Text(required=True)
    provider = fields.Char(help='What produced the answer: Gemini, OpenAI, internal, lead')
    qa_id = fields.Many2one('isd.ai.chatbot.qa', string='Q&A Used', ondelete='set null')
    citation_count = fields.Integer(string='Documents Cited')
    external_message_id = fields.Char(index=True, copy=False,
                                      help='Channel message id (Facebook mid), used to ignore redeliveries')
