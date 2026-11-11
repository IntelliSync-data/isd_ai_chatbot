# -*- coding: utf-8 -*-
"""REST API for leads.

Creating a lead is open, like the contact form it stands beside. Everything
else needs the API key from Settings: isd_chatbot let anyone who knew the URL
list every customer and delete them, and pick which member of staff a lead
went to.
"""
import hmac
import json
import logging

from odoo import fields, http
from odoo.http import request

from .main import _rate_ok
from ..services.text import clean_phone, valid_email

_logger = logging.getLogger(__name__)

PUBLIC_SOURCES = ('api', 'website', 'manual')
WRITABLE = ('name', 'email', 'phone', 'topic', 'message', 'note', 'consultation_datetime', 'state')


def _reply(data, status=200):
    return request.make_response(json.dumps(data, ensure_ascii=False, default=str), status=status,
                                 headers=[('Content-Type', 'application/json; charset=utf-8')])


def _authorized():
    expected = request.env['isd.ai.chatbot.config'].sudo().get_config().api_key or ''
    given = request.httprequest.headers.get('X-API-Key') or ''
    auth = request.httprequest.headers.get('Authorization') or ''
    if not given and auth.lower().startswith('bearer '):
        given = auth[7:].strip()
    return bool(expected) and bool(given) and hmac.compare_digest(given, expected)


def _serialize(lead):
    return {
        'id': lead.id,
        'name': lead.name,
        'email': lead.email or None,
        'phone': lead.phone or None,
        'topic': lead.topic or None,
        'message': lead.message or None,
        'state': lead.state,
        'consultation_datetime': fields.Datetime.to_string(lead.consultation_datetime) or None,
        'source': lead.source_id.code or None,
        'assigned_user': lead.assigned_user_id.login or None,
        'crm_lead_id': lead.crm_lead_id.id or None,
        'created': fields.Datetime.to_string(lead.create_date),
    }


def _clean(data, allow_private):
    vals, errors = {}, []
    if 'name' in data:
        vals['name'] = str(data['name'] or '').strip()[:100]
    if 'email' in data:
        vals['email'] = valid_email(data['email']) or False
        if data['email'] and not vals['email']:
            errors.append('email is not valid')
    if 'phone' in data:
        vals['phone'] = clean_phone(str(data['phone'] or '')) or False
        if data['phone'] and not vals['phone']:
            errors.append('phone must have 8 to 15 digits')
    for key in ('topic', 'message', 'note'):
        if key in data:
            vals[key] = str(data[key] or '').strip()[:4000] or False
    if data.get('consultation_datetime'):
        try:
            vals['consultation_datetime'] = fields.Datetime.to_datetime(data['consultation_datetime'])
        except ValueError:
            errors.append('consultation_datetime must be "YYYY-MM-DD HH:MM:SS" in UTC')
    if allow_private:
        if data.get('state'):
            vals['state'] = data['state']
        if data.get('assigned_user_email'):
            user = request.env['res.users'].sudo().search([('email', '=ilike', data['assigned_user_email'])], limit=1)
            if not user:
                errors.append('no user with email %s' % data['assigned_user_email'])
            vals['assigned_user_id'] = user.id
    return vals, errors


class IsdAiChatbotRest(http.Controller):

    @http.route('/isd_ai_chatbot/api/v1/leads', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def create(self, **kw):
        private = _authorized()
        if not private and not _rate_ok('rest', 10, 600):
            return _reply({'success': False, 'error': 'rate limited'}, 429)
        try:
            data = json.loads(request.httprequest.get_data() or b'{}')
        except ValueError:
            return _reply({'success': False, 'error': 'body must be JSON'}, 400)
        vals, errors = _clean(data, private)
        if not vals.get('name'):
            errors.append('name is required')
        if not vals.get('email') and not vals.get('phone'):
            errors.append('email or phone is required')
        code = str(data.get('source_code') or 'api')
        if not private and code not in PUBLIC_SOURCES:
            code = 'api'
        if errors:
            return _reply({'success': False, 'errors': errors}, 400)
        source = request.env['isd.ai.chatbot.source']._by_code(code)
        lead = request.env['isd.ai.chatbot.lead'].sudo().create(dict(vals, source_id=source.id or False))
        return _reply({'success': True, 'data': _serialize(lead)}, 201)

    @http.route('/isd_ai_chatbot/api/v1/leads', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def list(self, state=None, limit='50', offset='0', **kw):
        if not _authorized():
            return _reply({'success': False, 'error': 'API key required'}, 401)
        domain = [('state', '=', state)] if state else []
        Lead = request.env['isd.ai.chatbot.lead'].sudo()
        limit, offset = max(1, min(int(limit or 50), 200)), max(0, int(offset or 0))
        leads = Lead.search(domain, limit=limit, offset=offset)
        return _reply({'success': True, 'total': Lead.search_count(domain),
                       'data': [_serialize(lead) for lead in leads]})

    @http.route('/isd_ai_chatbot/api/v1/leads/<int:lead_id>', type='http', auth='public',
                methods=['GET', 'PUT', 'DELETE', 'OPTIONS'], csrf=False, cors='*')
    def one(self, lead_id, **kw):
        if not _authorized():
            return _reply({'success': False, 'error': 'API key required'}, 401)
        lead = request.env['isd.ai.chatbot.lead'].sudo().browse(lead_id).exists()
        if not lead:
            return _reply({'success': False, 'error': 'not found'}, 404)
        method = request.httprequest.method
        if method == 'DELETE':
            lead.unlink()
            return _reply({'success': True})
        if method == 'PUT':
            try:
                data = json.loads(request.httprequest.get_data() or b'{}')
            except ValueError:
                return _reply({'success': False, 'error': 'body must be JSON'}, 400)
            vals, errors = _clean({k: v for k, v in data.items() if k in WRITABLE + ('assigned_user_email',)}, True)
            if errors:
                return _reply({'success': False, 'errors': errors}, 400)
            lead.write(vals)
        return _reply({'success': True, 'data': _serialize(lead)})
