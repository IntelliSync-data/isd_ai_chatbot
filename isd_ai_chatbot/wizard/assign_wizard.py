# -*- coding: utf-8 -*-
from odoo import fields, models


class IsdAiChatbotLeadAssignWizard(models.TransientModel):
    _name = 'isd.ai.chatbot.lead.assign.wizard'
    _description = 'Assign a Chatbot Lead'

    lead_id = fields.Many2one('isd.ai.chatbot.lead', required=True)
    assigned_user_id = fields.Many2one('res.users', string='Assign To', required=True,
                                       domain=[('share', '=', False)], default=lambda self: self.env.user)
    next_action = fields.Selection([('crm', 'Save to CRM'), ('book', 'Book Meeting')])

    def action_confirm(self):
        self.ensure_one()
        self.lead_id.assigned_user_id = self.assigned_user_id
        if self.next_action == 'crm':
            return self.lead_id.action_save_to_crm()
        if self.next_action == 'book':
            return self.lead_id.action_book_meeting()
        return {'type': 'ir.actions.act_window_close'}
