# -*- coding: utf-8 -*-
"""Leads pushed to CRM before 18.0.1.1.0 were always of type 'lead'. With
CRM's Leads setting off they never showed anywhere, so they become
opportunities, the way CRM would have created them."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Lead = env['isd.ai.chatbot.lead']
    if Lead._crm_type() == 'lead':
        return
    hidden = Lead.with_context(active_test=False).search([]).crm_lead_id.filtered(
        lambda crm: crm.type == 'lead')
    for crm in hidden:
        crm.convert_opportunity(crm.partner_id)
    _logger.info('isd_ai_chatbot: %s chatbot leads moved to the CRM pipeline', len(hidden))
