# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_ai_chatbot_agent = fields.Boolean(
        string='Takes Chatbot Leads',
        help='New chatbot leads are shared out between users with this ticked, fewest open leads first')
