# -*- coding: utf-8 -*-
import json
import logging
import os
import time
import uuid
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_path

from ..services.channels import FacebookChannel, ZaloChannel
from ..services.engine import ChatEngine
from ..services.lead_extract import find_phone
from ..services.text import clean_phone, valid_email, valid_session_id

_logger = logging.getLogger(__name__)

# Per-process counters: with several Odoo workers each keeps its own, so the
# real ceiling is the limit times the worker count. Enough to stop a script
# from burning the language-model quota.
_BUCKETS = {}
ASSET_FIELDS = ('avatar', 'icon_toggle', 'icon_chat', 'icon_phone', 'icon_zalo', 'icon_messenger')
STATIC_DIR = os.path.join(get_module_path('isd_ai_chatbot') or '', 'static', 'src')


def _client_ip():
    # Behind a proxy, Odoo's proxy_mode has already put the real address
    # here. Reading X-Forwarded-For directly, as chatbot_ai_rag did, lets
    # anyone dodge the rate limit by sending a different header each time.
    return request.httprequest.remote_addr or 'unknown'


def _rate_ok(bucket, limit, window):
    now = time.time()
    if len(_BUCKETS) > 5000:
        for key in [k for k, v in _BUCKETS.items() if now > v[1]]:
            _BUCKETS.pop(key, None)
    key = '%s:%s' % (bucket, _client_ip())
    entry = _BUCKETS.get(key)
    if not entry or now > entry[1]:
        _BUCKETS[key] = [1, now + window]
        return True
    if entry[0] >= limit:
        return False
    entry[0] += 1
    return True


def _json(data, status=200):
    return request.make_response(json.dumps(data, ensure_ascii=False), status=status,
                                 headers=[('Content-Type', 'application/json; charset=utf-8')])


def _body():
    try:
        return json.loads(request.httprequest.get_data() or b'{}')
    except ValueError:
        return {}


def _origin_allowed(config):
    allowed = config._allowed_origins()
    origin = (request.httprequest.headers.get('Origin') or '').rstrip('/')
    if not allowed or not origin:
        return True
    base = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
    return origin in allowed or origin == base


class IsdAiChatbotController(http.Controller):

    # --------------------------------------------------------------- widget
    def _static(self, rel_path, content_type):
        with open(os.path.join(STATIC_DIR, rel_path), 'rb') as fh:
            data = fh.read()
        return request.make_response(data, headers=[
            ('Content-Type', content_type),
            # Short, so a fix reaches sites embedding the widget the same day
            ('Cache-Control', 'public, max-age=300'),
            ('Access-Control-Allow-Origin', '*'),
        ])

    @http.route('/isd_ai_chatbot/widget.js', type='http', auth='public', methods=['GET'], csrf=False)
    def widget_js(self, **kw):
        return self._static('js/widget.js', 'application/javascript; charset=utf-8')

    @http.route('/isd_ai_chatbot/widget.css', type='http', auth='public', methods=['GET'], csrf=False)
    def widget_css(self, **kw):
        return self._static('css/widget.css', 'text/css; charset=utf-8')

    @http.route('/isd_ai_chatbot/asset/<string:field>', type='http', auth='public', methods=['GET'], csrf=False)
    def asset(self, field, **kw):
        """The avatar and button icons. Served here rather than through
        /web/image, which would need public read access to the settings
        record - and with it the API keys."""
        if field not in ASSET_FIELDS:
            return request.not_found()
        config = request.env['isd.ai.chatbot.config'].sudo().get_config()
        if not config[field]:
            return request.not_found()
        stream = request.env['ir.binary']._get_image_stream_from(config, field)
        response = stream.get_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    @http.route('/isd_ai_chatbot/api/config', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def public_config(self, **kw):
        cfg = request.env['isd.ai.chatbot.config'].sudo().get_config()
        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')

        def asset_url(field):
            return '%s/isd_ai_chatbot/asset/%s?v=%s' % (base, field, int(cfg.write_date.timestamp())) \
                if cfg[field] else ''

        def texts(field):
            return {'vi': cfg._text(field, 'vi'), 'en': cfg._text(field, 'en')}

        return _json({
            'botTitle': cfg.bot_title or 'AI Assistant',
            'botSubtitle': cfg.bot_subtitle or '',
            'primaryColor': cfg.primary_color or '#0b53cb',
            'secondaryColor': cfg.secondary_color or '#1d4ed8',
            'avatarUrl': asset_url('avatar'),
            'greeting': texts('greeting'),
            'welcome': texts('welcome_message'),
            'suggested': {'vi': cfg._suggested_questions('vi'), 'en': cfg._suggested_questions('en')},
            'buttons': {
                'chat': bool(cfg.show_chat_button),
                'phone': cfg.phone or '',
                'zalo': cfg.zalo_link or '',
                'messenger': cfg.messenger_link or '',
            },
            'colors': {
                'toggle': cfg.color_toggle, 'chat': cfg.color_chat, 'phone': cfg.color_phone,
                'zalo': cfg.color_zalo, 'messenger': cfg.color_messenger,
            },
            'icons': {k: asset_url('icon_%s' % k) for k in ('toggle', 'chat', 'phone', 'zalo', 'messenger')},
        })

    # ----------------------------------------------------------------- chat
    @http.route('/isd_ai_chatbot/api/chat', type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False, cors='*')
    def chat(self, **kw):
        config = request.env['isd.ai.chatbot.config'].sudo().get_config()
        if not _origin_allowed(config):
            return _json({'ok': False, 'error': 'origin not allowed'}, 403)
        if not _rate_ok('chat', 25, 60):
            return _json({'ok': False, 'error': 'Too many messages, please wait a moment.'}, 429)
        body = _body()
        text = str(body.get('message') or '').strip()[:1000]
        if not text:
            return _json({'ok': False, 'error': 'empty message'}, 400)
        session_id = valid_session_id(body.get('session_id')) or uuid.uuid4().hex

        conv = request.env['isd.ai.chatbot.conversation'].sudo()._get_or_create(
            session_id, 'website', user_ip=_client_ip(),
            user_agent=(request.httprequest.user_agent.string or '')[:250],
            page_url=str(body.get('page_url') or '')[:500] or False)
        try:
            result = ChatEngine(request.env).reply(conv, text, lang_hint=str(body.get('lang') or ''))
        except Exception:
            _logger.exception("isd_ai_chatbot: chat failed for session %s", session_id)
            return _json({'ok': False, 'error': 'The assistant is unavailable right now.'}, 500)
        return _json({
            'ok': True,
            'sessionId': session_id,
            'reply': result['reply'],
            'lang': result['lang'],
            'citations': result.get('citations') or [],
            'showLeadForm': bool(result.get('show_lead_form')),
            'leadCaptured': bool(result.get('lead_captured')),
            'provider': result.get('provider') or '',
        })

    @http.route('/isd_ai_chatbot/api/lead', type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False, cors='*')
    def submit_lead(self, **kw):
        """The contact form in the widget. Name, plus a phone or an email."""
        config = request.env['isd.ai.chatbot.config'].sudo().get_config()
        if not _origin_allowed(config):
            return _json({'ok': False, 'error': 'origin not allowed'}, 403)
        if not _rate_ok('lead', 5, 600):
            return _json({'ok': False, 'error': 'Too many requests, please try again later.'}, 429)
        body = _body()
        name = str(body.get('name') or '').strip()[:100]
        email = valid_email(body.get('email'))
        phone = clean_phone(str(body.get('phone') or '')) or find_phone(str(body.get('phone') or ''))
        if not name or not (email or phone):
            return _json({'ok': False, 'error': 'name and a phone or email are required'}, 400)

        session_id = valid_session_id(body.get('session_id')) or uuid.uuid4().hex
        conv = request.env['isd.ai.chatbot.conversation'].sudo()._get_or_create(
            session_id, 'website', user_ip=_client_ip())
        vals = {'lead_name': name, 'lead_state': 'done'}
        if email:
            vals['lead_email'] = email
        if phone:
            vals['lead_phone'] = phone
        topic = str(body.get('message') or '').strip()[:500]
        if topic:
            vals['lead_topic'] = topic
        when = str(body.get('datetime') or '').strip()
        if when:
            try:
                vals['lead_datetime'] = datetime.strptime(when[:16], '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:00')
            except ValueError:
                pass
        conv.write(vals)
        if topic:
            conv._log_message('user', topic)
        lead = conv._upsert_lead()
        return _json({'ok': True, 'sessionId': session_id, 'leadId': lead.id})

    # ------------------------------------------------------------- webhooks
    @http.route('/isd_ai_chatbot/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def webhook(self, **kw):
        """One address for both channels, told apart by ?merchant=zalo|facebook.

        Always answers 200 to a provider, so a failure on our side is
        recorded in the webhook log rather than retried at us forever."""
        req = request.httprequest
        merchant = (req.args.get('merchant') or '').strip().lower()
        raw = req.get_data() or b''
        headers = {k: v for k, v in req.headers.items() if k.lower() not in ('authorization', 'cookie')}
        log = request.env['isd.ai.chatbot.webhook.log'].sudo().create({
            'merchant': merchant if merchant in ('zalo', 'facebook') else 'other',
            'http_method': req.method,
            'source_ip': _client_ip(),
            'user_agent': (req.user_agent.string or '')[:250],
            'headers': json.dumps(headers, indent=2)[:4000],
            'body': raw.decode('utf-8', errors='replace')[:20000] or json.dumps(dict(req.args)),
        })
        config = request.env['isd.ai.chatbot.config'].sudo().get_config()
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {}
        try:
            if merchant == 'facebook':
                return self._facebook(config, log, req, raw, payload)
            if merchant == 'zalo':
                return self._zalo(config, log, req, raw, payload)
            log.write({'status': 'ignored', 'note': 'missing or unknown merchant'})
        except Exception as e:
            _logger.exception("isd_ai_chatbot: webhook %s failed", merchant)
            log.write({'status': 'error', 'note': str(e)[:1000]})
        return request.make_response('', status=200)

    def _zalo(self, config, log, req, raw, payload):
        channel = ZaloChannel(config)
        if not config.zalo_enabled:
            log.write({'status': 'ignored', 'note': 'Zalo is switched off in Settings'})
            return request.make_response('', status=200)
        if not channel.verify_signature(raw, req.headers, payload):
            log.write({'status': 'rejected', 'note': 'bad X-ZEvent-Signature'})
            return request.make_response('', status=200)
        sender_id, text = channel.parse(payload)
        if not (sender_id and text):
            log.write({'status': 'ignored', 'note': 'not a customer text message (%s)' % payload.get('event_name')})
            return request.make_response('', status=200)
        conv = request.env['isd.ai.chatbot.conversation'].sudo()._get_or_create(
            'zalo:%s' % sender_id, 'zalo', user_ip=_client_ip())
        result = ChatEngine(request.env).reply(conv, text[:1000])
        error = channel.send_text(sender_id, result['reply'])
        log.write({'status': 'error' if error else 'processed', 'note': error or False})
        return request.make_response('', status=200)

    def _facebook(self, config, log, req, raw, payload):
        channel = FacebookChannel(config)
        if req.method == 'GET':
            challenge = channel.verify_subscription(dict(req.args))
            if challenge is None:
                log.write({'status': 'rejected', 'note': 'subscription check failed'})
                return request.make_response('', status=403)
            log.write({'status': 'processed', 'note': 'subscription check passed'})
            return request.make_response(challenge, status=200, headers=[('Content-Type', 'text/plain')])
        if not config.facebook_enabled:
            log.write({'status': 'ignored', 'note': 'Facebook is switched off in Settings'})
            return request.make_response('', status=200)
        if not channel.verify_signature(raw, req.headers.get('X-Hub-Signature-256', '')):
            log.write({'status': 'rejected', 'note': 'bad X-Hub-Signature-256'})
            return request.make_response('', status=200)

        Message = request.env['isd.ai.chatbot.message'].sudo()
        notes, handled = [], 0
        for psid, text, mid in channel.iter_text_events(payload):
            # Facebook redelivers when we answer slowly; answer each message once
            if mid and Message.search_count([('external_message_id', '=', mid)]):
                notes.append('duplicate %s' % mid)
                continue
            conv = request.env['isd.ai.chatbot.conversation'].sudo()._get_or_create(
                'facebook:%s' % psid, 'facebook', user_ip=_client_ip())
            result = ChatEngine(request.env).reply(conv, text[:1000], external_message_id=mid)
            error = channel.send_text(psid, result['reply'])
            if error:
                notes.append('send to %s failed: %s' % (psid, error))
            handled += 1
        status = 'error' if any('failed' in n for n in notes) else ('processed' if handled else 'ignored')
        log.write({'status': status, 'note': '; '.join(notes) or (False if handled else 'no text messages')})
        return request.make_response('', status=200)
