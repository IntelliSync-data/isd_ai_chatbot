# -*- coding: utf-8 -*-
from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    # Read by the layout template, which cannot query the settings itself.
    # Per website, because one database can carry several sites and only some
    # of them may want the bubble.
    isd_ai_chatbot_enabled = fields.Boolean(compute='_compute_isd_ai_chatbot_enabled')

    def _compute_isd_ai_chatbot_enabled(self):
        enabled = self.env['isd.ai.chatbot.config'].sudo().get_config().website_ids
        for website in self:
            website.isd_ai_chatbot_enabled = website in enabled
