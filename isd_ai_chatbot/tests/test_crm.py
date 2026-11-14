# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestCrmPush(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(cls.env, login='bot_agent', groups='base.group_user,sales_team.group_sale_salesman',
                                  email='agent@example.com')
        cls.config = cls.env['isd.ai.chatbot.config'].get_config()
        cls.config.write({'auto_assign': False, 'auto_crm': False})
        cls.use_leads = cls.env.ref('crm.group_use_lead')
        cls.employee = cls.env.ref('base.group_user')

    def _set_leads_setting(self, on):
        self.employee.sudo().write({'implied_ids': [(4 if on else 3, self.use_leads.id)]})

    def _lead(self, **vals):
        return self.env['isd.ai.chatbot.lead'].create(dict(
            {'name': 'Nguyen Van A', 'phone': '0901234567', 'assigned_user_id': self.agent.id}, **vals))

    def _in_pipeline(self, crm):
        """What the CRM app shows: the Pipeline menu lists opportunities only."""
        return crm in self.env['crm.lead'].search([('type', '=', 'opportunity')])

    def test_save_to_crm_shows_in_pipeline(self):
        # CRM's Leads setting is off by default: a 'lead' would be invisible
        self._set_leads_setting(False)
        lead = self._lead()
        lead.action_save_to_crm()
        self.assertEqual(lead.crm_lead_id.type, 'opportunity')
        self.assertTrue(lead.crm_lead_id.stage_id, 'an opportunity without a stage falls out of the pipeline')
        self.assertTrue(self._in_pipeline(lead.crm_lead_id))
        self.assertEqual(lead.crm_lead_id.user_id, self.agent)
        self.assertEqual(lead.state, 'crm')
        self.assertEqual(lead.action_open_crm()['res_id'], lead.crm_lead_id.id)

    def test_leads_setting_on_creates_lead(self):
        self._set_leads_setting(True)
        lead = self._lead()
        lead.action_save_to_crm()
        self.assertEqual(lead.crm_lead_id.type, 'lead')

    def test_booking_pushes_to_crm(self):
        self._set_leads_setting(False)
        lead = self._lead(consultation_datetime=datetime(2030, 1, 15, 3, 0))
        lead.action_book_meeting()
        self.assertTrue(self._in_pipeline(lead.crm_lead_id))
        self.assertEqual(lead.calendar_event_id.opportunity_id, lead.crm_lead_id)
        self.assertEqual(lead.state, 'booked')

    def test_automatic_push(self):
        self._set_leads_setting(False)
        self.config.auto_crm = True
        lead = self._lead()
        self.assertTrue(self._in_pipeline(lead.crm_lead_id))
