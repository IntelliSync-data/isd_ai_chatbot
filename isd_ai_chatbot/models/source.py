# -*- coding: utf-8 -*-
from odoo import fields, models


class IsdAiChatbotSource(models.Model):
    _name = 'isd.ai.chatbot.source'
    _description = 'AI Chatbot Lead Source'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, help='Technical key used by the API, e.g. website, zalo')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [('code_unique', 'unique(code)', 'Each source code must be unique.')]

    def _by_code(self, code):
        return self.sudo().search([('code', '=', code)], limit=1)
