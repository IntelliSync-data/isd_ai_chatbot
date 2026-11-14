# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..services import llm

_logger = logging.getLogger(__name__)


class IsdAiChatbotLead(models.Model):
    _name = 'isd.ai.chatbot.lead'
    _description = 'AI Chatbot Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    email = fields.Char(tracking=True)
    phone = fields.Char(tracking=True)
    topic = fields.Char(help='What the customer wants to discuss, as they put it')
    message = fields.Text(string='Customer Messages', help='What the customer wrote in the chat')
    note = fields.Text(string='Internal Note')
    lang = fields.Selection([('vi', 'Vietnamese'), ('en', 'English')], default='vi')
    consultation_datetime = fields.Datetime(string='Meeting Time', tracking=True)
    meeting_time_display = fields.Char(
        compute='_compute_meeting_time_display',
        help='The meeting time on the customer clock, for emails')
    state = fields.Selection([
        ('new', 'New'),
        ('crm', 'In CRM'),
        ('booked', 'Meeting Booked'),
        ('cancelled', 'Cancelled'),
    ], default='new', required=True, tracking=True, index=True)

    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True, index=True,
                                       domain=[('share', '=', False)])
    source_id = fields.Many2one('isd.ai.chatbot.source', string='Source', ondelete='restrict',
                                default=lambda self: self.env['isd.ai.chatbot.source']._by_code('manual'))
    conversation_id = fields.Many2one('isd.ai.chatbot.conversation', string='Conversation', readonly=True,
                                      ondelete='set null')
    conversation_message_count = fields.Integer(related='conversation_id.message_count', string='Chat Messages')
    crm_lead_id = fields.Many2one('crm.lead', string='CRM Lead', readonly=True, copy=False)
    calendar_event_id = fields.Many2one('calendar.event', string='Meeting', readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True, copy=False)

    analyzed = fields.Boolean(readonly=True, copy=False)
    analysis_date = fields.Datetime(readonly=True, copy=False)
    analysis_log = fields.Text(readonly=True, copy=False)

    hide_analyze_button = fields.Boolean(compute='_compute_ui_flags')
    hide_crm_button = fields.Boolean(compute='_compute_ui_flags')

    # create_date is UTC; this is the same day as the user lives it, so a
    # "Today" filter means today where they sit
    create_date_local = fields.Date(string='Created On', compute='_compute_create_date_local',
                                    search='_search_create_date_local')

    @api.constrains('email', 'phone')
    def _check_contact(self):
        for rec in self:
            if not rec.email and not rec.phone:
                raise ValidationError(_('A lead needs an email or a phone number.'))

    def _compute_ui_flags(self):
        config = self.env['isd.ai.chatbot.config'].sudo().get_config()
        for rec in self:
            rec.hide_analyze_button = config.hide_analyze_button or not config.has_language_model
            rec.hide_crm_button = config.hide_crm_button

    @api.depends('consultation_datetime')
    def _compute_meeting_time_display(self):
        tz = pytz.timezone(self.env['isd.ai.chatbot.config'].sudo().get_config().timezone or 'UTC')
        for rec in self:
            rec.meeting_time_display = pytz.utc.localize(rec.consultation_datetime).astimezone(tz).strftime(
                '%d/%m/%Y %H:%M') if rec.consultation_datetime else ''

    @api.depends('create_date')
    def _compute_create_date_local(self):
        for rec in self:
            rec.create_date_local = fields.Datetime.context_timestamp(
                rec, rec.create_date).date() if rec.create_date else False

    def _search_create_date_local(self, operator, value):
        tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')

        def boundary(day, end=False):
            naive = datetime.combine(day, time.max if end else time.min)
            return fields.Datetime.to_string(tz.localize(naive).astimezone(pytz.utc).replace(tzinfo=None))

        day = fields.Date.to_date(value)
        if operator == '=':
            return [('create_date', '>=', boundary(day)), ('create_date', '<=', boundary(day, True))]
        if operator in ('>=', '>'):
            return [('create_date', operator, boundary(day, end=(operator == '>')))]
        if operator in ('<=', '<'):
            return [('create_date', operator, boundary(day, end=(operator == '<=')))]
        raise UserError(_('This filter does not support the operator %s.') % operator)

    # ------------------------------------------------------------- creation
    @api.model_create_multi
    def create(self, vals_list):
        config = self.env['isd.ai.chatbot.config'].sudo().get_config()
        for vals in vals_list:
            if not vals.get('assigned_user_id') and config.auto_assign:
                vals['assigned_user_id'] = self._next_agent().id
        leads = super().create(vals_list)
        for lead in leads.filtered('assigned_user_id'):
            lead._notify_assignee()
        if config.auto_crm:
            for lead in leads:
                try:
                    lead._create_crm_lead()
                except Exception:
                    # A CRM problem must never lose the lead itself
                    _logger.exception("isd_ai_chatbot: automatic CRM push failed for lead %s", lead.id)
        return leads

    def write(self, vals):
        before = {rec.id: rec.assigned_user_id for rec in self} if 'assigned_user_id' in vals else {}
        res = super().write(vals)
        for rec in self:
            if before and rec.assigned_user_id and rec.assigned_user_id != before.get(rec.id):
                rec._notify_assignee()
        return res

    @api.model
    def _next_agent(self):
        """The agent with the fewest open leads.

        isd_chatbot had an "is chatbot agent" flag on users and then shared
        leads out between every internal user regardless - accountants
        included. Only flagged agents take leads here; with none flagged, the
        lead is left for a manager to assign.
        """
        agents = self.env['res.users'].sudo().search([('is_ai_chatbot_agent', '=', True), ('share', '=', False)])
        if not agents:
            return self.env['res.users']
        counts = dict(self.sudo()._read_group(
            [('assigned_user_id', 'in', agents.ids), ('state', 'in', ('new', 'crm'))],
            ['assigned_user_id'], ['__count']))
        return min(agents, key=lambda u: (counts.get(u, 0), u.id))

    def _notify_assignee(self):
        self.ensure_one()
        self.activity_schedule(
            'mail.mail_activity_data_todo', user_id=self.assigned_user_id.id,
            summary=_('New chatbot lead: %s') % self.name,
            note=_('Contact: %s') % ' / '.join(x for x in (self.phone, self.email) if x))

    # -------------------------------------------------------------- actions
    def _ensure_assigned(self, next_action):
        self.ensure_one()
        if self.assigned_user_id:
            return None
        return {
            'name': _('Assign Lead'),
            'type': 'ir.actions.act_window',
            'res_model': 'isd.ai.chatbot.lead.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lead_id': self.id, 'default_next_action': next_action},
        }

    def _find_or_create_partner(self):
        self.ensure_one()
        Partner = self.env['res.partner'].sudo()
        partner = Partner.browse()
        if self.email:
            partner = Partner.search([('email', '=ilike', self.email)], limit=1)
        if not partner and self.phone:
            partner = Partner.search([('phone', '=', self.phone)], limit=1)
        if not partner:
            partner = Partner.create({'name': self.name, 'email': self.email or False, 'phone': self.phone or False})
        elif self.phone and not partner.phone:
            partner.phone = self.phone
        self.partner_id = partner
        return partner

    @api.model
    def _crm_type(self):
        """CRM's own rule: records of type 'lead' only show when the Leads
        setting is on. With it off (Odoo's default) they sit in the database
        out of sight, so the pipeline needs an opportunity."""
        use_leads = self.env.ref('crm.group_use_lead') in self.env.ref('base.group_user').sudo().implied_ids
        return 'lead' if use_leads else 'opportunity'

    def _create_crm_lead(self):
        self.ensure_one()
        if self.crm_lead_id:
            return self.crm_lead_id
        partner = self._find_or_create_partner()
        team = self.assigned_user_id.sale_team_id if self.assigned_user_id else self.env['crm.team']
        description = '\n\n'.join(x for x in (
            self.topic and _('Topic: %s') % self.topic,
            self.message,
            self.note,
        ) if x)
        crm = self.env['crm.lead'].sudo().create({
            'name': _('Chatbot - %s') % self.name,
            'type': self._crm_type(),
            'contact_name': self.name,
            'email_from': self.email or False,
            'phone': self.phone or False,
            'partner_id': partner.id,
            'user_id': self.assigned_user_id.id or False,
            'team_id': team.id or False,
            'description': description,
        })
        self.write({'crm_lead_id': crm.id, 'state': 'crm' if self.state == 'new' else self.state})
        return crm

    def action_save_to_crm(self):
        self.ensure_one()
        if self.crm_lead_id:
            raise UserError(_('This lead is already in CRM.'))
        wizard = self._ensure_assigned('crm')
        if wizard:
            return wizard
        crm = self._create_crm_lead()
        return self._notify(_('CRM lead created and linked to %s.') % crm.partner_id.display_name)

    def action_set_meeting_time(self):
        self.ensure_one()
        return {
            'name': _('Meeting Time'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('isd_ai_chatbot.view_lead_meeting_time_form').id,
            'target': 'new',
        }

    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_book_meeting(self):
        """A calendar event with a Discuss video link, and the invitations sent."""
        self.ensure_one()
        if self.calendar_event_id:
            raise UserError(_('A meeting is already booked for this lead.'))
        if not self.consultation_datetime:
            return self.action_set_meeting_time()
        wizard = self._ensure_assigned('book')
        if wizard:
            return wizard
        if not self.crm_lead_id:
            self._create_crm_lead()
        partner = self.partner_id or self._find_or_create_partner()
        event = self.env['calendar.event'].sudo().create({
            'name': _('Consultation - %s') % self.name,
            'start': self.consultation_datetime,
            'stop': self.consultation_datetime + timedelta(hours=1),
            'user_id': self.assigned_user_id.id,
            'partner_ids': [(6, 0, (partner | self.assigned_user_id.partner_id).ids)],
            'opportunity_id': self.crm_lead_id.id or False,
            'description': self.topic or self.message or '',
        })
        # Odoo 18 derives videocall_source from the location; setting the
        # Discuss location is what makes the link
        event._set_discuss_videocall_location()
        self.write({'calendar_event_id': event.id, 'state': 'booked'})
        sent = self._send_booking_emails()
        return self._notify(_('Meeting booked. %s') % sent)

    def _send_booking_emails(self):
        """isd_chatbot referred to two email templates that never existed, so
        its booking confirmation was never sent. These ones do exist."""
        self.ensure_one()
        sent = []
        if self.email:
            self.env.ref('isd_ai_chatbot.mail_template_booking_customer').sudo().send_mail(self.id, force_send=True)
            sent.append(self.email)
        if self.assigned_user_id.email:
            self.env.ref('isd_ai_chatbot.mail_template_booking_agent').sudo().send_mail(self.id, force_send=True)
            sent.append(self.assigned_user_id.email)
        return _('Invitation sent to %s.') % ', '.join(sent) if sent else _('No email address to send the invitation to.')

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'new'})

    def action_analyze(self):
        """Read name, email, phone and meeting time out of the customer's messages."""
        self.ensure_one()
        if not self.message:
            raise UserError(_('There are no customer messages to analyze.'))
        config = self.env['isd.ai.chatbot.config'].sudo().get_config()
        data, log = llm.extract_contact(config, self.message)
        updates = {'analysis_log': '\n'.join(log), 'analysis_date': fields.Datetime.now()}
        if data:
            updates['analyzed'] = True
            for key in ('name', 'email', 'phone'):
                if data.get(key):
                    updates[key] = data[key]
            if data.get('datetime'):
                when = self.conversation_id._local_datetime_to_utc(data['datetime'] + ':00') \
                    if len(data['datetime']) == 16 else False
                if when:
                    updates['consultation_datetime'] = when
        self.write(updates)
        if not data:
            raise UserError('\n'.join(log))

    def action_open_crm(self):
        self.ensure_one()
        # CRM's menu actions carry no path, so a bare action is what gives a
        # readable URL here: /odoo/.../crm.lead/<id>
        return {
            'type': 'ir.actions.act_window',
            'name': self.crm_lead_id.display_name,
            'res_model': 'crm.lead',
            'res_id': self.crm_lead_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_open_conversation(self):
        self.ensure_one()
        # The menu action, so the URL reads /odoo/.../ai-chatbot-conversations/<id>
        action = self.env['ir.actions.act_window']._for_xml_id('isd_ai_chatbot.action_conversation')
        action.update({'res_id': self.conversation_id.id, 'views': [(False, 'form')], 'view_mode': 'form'})
        return action

    def _notify(self, message):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': message, 'type': 'success', 'sticky': False,
                           'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}}}
