# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IsdAiChatbotLead(models.Model):
    _inherit = 'isd.ai.chatbot.lead'

    student_id = fields.Many2one('op.student', string='Student', readonly=True, copy=False)
    survey_user_input_id = fields.Many2one('survey.user_input', string='Survey Response', readonly=True, copy=False)
    # A key, not a label: the view tests it, and a translated label would
    # never equal the English string the view compares against
    invite_state = fields.Selection([('none', 'Nothing to Do'), ('invite', 'Invite'), ('resend', 'Resend')],
                                    compute='_compute_invite_state')

    @api.depends('email')
    def _compute_invite_state(self):
        Users = self.env['res.users'].sudo()
        for rec in self:
            user = Users.search([('login', '=ilike', rec.email)], limit=1) if rec.email else Users
            if not rec.email or (user and user.login_date):
                rec.invite_state = 'none'
            else:
                rec.invite_state = 'resend' if user else 'invite'

    def action_invite_student(self):
        """Student record, portal login, invitation email, pre-filled survey.

        Two changes from isd_chatbot. The login is a portal user made by
        OpenEduCat's own create_student_user, not an internal user from
        web_create_users, which gave every student back-office access and,
        on Enterprise, a paid seat. And the survey response is kept on the
        lead: isd_chatbot wrote it onto op.student fields that no module
        defines, so with a survey mapping in place every invitation failed.
        """
        self.ensure_one()
        if not self.email:
            raise UserError(_('The lead needs an email address to be invited.'))
        Users = self.env['res.users'].sudo()
        user = Users.search([('login', '=ilike', self.email)], limit=1)
        if user and user.login_date:
            raise UserError(_('%s already signs in to the system.') % self.email)

        partner = self.partner_id or self._find_or_create_partner()
        student = self.student_id or self.env['op.student'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not student:
            student = self.env['op.student'].sudo().create({'partner_id': partner.id, 'first_name': self.name})
        if not student.user_id:
            student.create_student_user()
        user = student.user_id or user
        user.with_context(create_user=True).action_reset_password()

        notes = [_('Invitation sent to %s.') % self.email]
        if not self.survey_user_input_id:
            if self._start_survey(partner):
                notes.append(_('Survey started with the answers already given.'))
        self.write({'student_id': student.id})
        return self._notify(' '.join(notes))

    def _start_survey(self, partner):
        mappings = self.env['isd.ai.chatbot.survey.mapping'].sudo().search([])
        if not mappings:
            return False
        survey = mappings[0].survey_id
        user_input = self.env['survey.user_input'].sudo().create({
            'survey_id': survey.id, 'partner_id': partner.id, 'email': self.email, 'test_entry': False,
        })
        for mapping in mappings.filtered(lambda m: m.survey_id == survey):
            value = self[mapping.lead_field]
            if value:
                self._prefill(user_input, mapping.question_id, value)
        self.survey_user_input_id = user_input
        return True

    def _prefill(self, user_input, question, value):
        vals = {'user_input_id': user_input.id, 'question_id': question.id,
                'answer_type': question.question_type, 'skipped': False}
        if question.question_type == 'char_box':
            vals['value_char_box'] = str(value)
        elif question.question_type == 'text_box':
            vals['value_text_box'] = str(value)
        elif question.question_type == 'numerical_box':
            try:
                vals['value_numerical_box'] = float(value)
            except (TypeError, ValueError):
                return
        else:
            return  # choice questions cannot be filled from free text
        self.env['survey.user_input.line'].sudo().create(vals)
