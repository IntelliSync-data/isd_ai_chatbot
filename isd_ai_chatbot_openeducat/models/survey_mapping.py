# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

LEAD_FIELDS = [('name', 'Name'), ('email', 'Email'), ('phone', 'Phone'), ('topic', 'Topic')]


class IsdAiChatbotSurveyMapping(models.Model):
    """Which survey question a lead's answer pre-fills."""
    _name = 'isd.ai.chatbot.survey.mapping'
    _description = 'AI Chatbot Survey Mapping'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    survey_id = fields.Many2one('survey.survey', required=True, ondelete='cascade')
    question_id = fields.Many2one('survey.question', required=True, ondelete='cascade',
                                  domain="[('survey_id', '=', survey_id)]")
    lead_field = fields.Selection(LEAD_FIELDS, string='Lead Field', required=True)

    @api.constrains('survey_id', 'lead_field', 'active')
    def _check_unique(self):
        for rec in self.filtered('active'):
            if self.search_count([('id', '!=', rec.id), ('survey_id', '=', rec.survey_id.id),
                                  ('lead_field', '=', rec.lead_field), ('active', '=', True)]):
                raise ValidationError(_('"%s" is already mapped to a question of this survey.')
                                      % dict(LEAD_FIELDS)[rec.lead_field])
