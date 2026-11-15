# -*- coding: utf-8 -*-
from odoo import fields, models


class IsdAiChatbotConfig(models.Model):
    _inherit = 'isd.ai.chatbot.config'

    hide_invite_button = fields.Boolean(string='Hide "Invite as User"')
