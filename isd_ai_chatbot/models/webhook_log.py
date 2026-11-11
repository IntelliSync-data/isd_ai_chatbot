# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IsdAiChatbotWebhookLog(models.Model):
    """Every inbound Zalo / Facebook call, kept for 30 days.

    When a channel stops answering, this is the first place to look: what
    arrived, whether it passed the signature check, and what went wrong
    sending the reply."""
    _name = 'isd.ai.chatbot.webhook.log'
    _description = 'AI Chatbot Webhook Log'
    _order = 'id desc'

    merchant = fields.Selection([('zalo', 'Zalo'), ('facebook', 'Facebook'), ('other', 'Other')], index=True)
    http_method = fields.Char(string='Method')
    source_ip = fields.Char(string='From IP')
    user_agent = fields.Char()
    headers = fields.Text()
    body = fields.Text()
    body_pretty = fields.Text(compute='_compute_body_pretty')
    status = fields.Selection([
        ('received', 'Received'), ('processed', 'Processed'), ('ignored', 'Ignored'),
        ('rejected', 'Rejected'), ('error', 'Error'),
    ], default='received', index=True)
    note = fields.Text()

    @api.depends('body')
    def _compute_body_pretty(self):
        for rec in self:
            try:
                rec.body_pretty = json.dumps(json.loads(rec.body or ''), indent=2, ensure_ascii=False)
            except ValueError:
                rec.body_pretty = rec.body

    @api.model
    def _cron_cleanup(self, days=30):
        """isd_chatbot's version called fields.timedelta, which odoo.fields does
        not have: the cron failed every day and logs were never removed."""
        old = self.sudo().search([('create_date', '<', fields.Datetime.now() - timedelta(days=days))])
        count = len(old)
        old.unlink()
        if count:
            _logger.info("isd_ai_chatbot: removed %s webhook logs older than %s days", count, days)
        return True
