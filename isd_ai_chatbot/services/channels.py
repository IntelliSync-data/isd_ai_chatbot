# -*- coding: utf-8 -*-
"""Sending replies to Zalo OA and Facebook Messenger, and checking that an
inbound webhook really came from them.

The token refresh logic is carried over from isd_chatbot, where it works in
production: Zalo answers error -216 on an expired access token, Facebook
answers OAuth error 190. Each refreshes once and resends once.
"""
import hashlib
import hmac
import json
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

_logger = logging.getLogger(__name__)


def _session(post_retries=False):
    s = requests.Session()
    methods = ['HEAD', 'GET', 'OPTIONS'] + (['POST'] if post_retries else [])
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504], allowed_methods=methods)
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s


class ZaloChannel:
    API = 'https://openapi.zalo.me/v3.0/oa'
    OAUTH = 'https://oauth.zaloapp.com/v4/oa/access_token'

    def __init__(self, config):
        self.config = config

    def verify_signature(self, raw_body, headers, payload):
        """Zalo signs each event: X-ZEvent-Signature = sha256(app_id + body + timestamp + OA secret).

        isd_chatbot checked nothing, so anyone who knew the URL could make the
        bot message any Zalo user through our OA. The check only runs once a
        webhook secret is set in Settings, so an existing setup keeps working
        until it is filled in.
        """
        secret = (self.config.zalo_webhook_secret or '').strip()
        if not secret:
            return True
        provided = (headers.get('X-ZEvent-Signature') or headers.get('x-zevent-signature') or '').strip()
        if provided.startswith('mac='):
            provided = provided[4:]
        timestamp = str((payload or {}).get('timestamp') or '')
        body = raw_body.decode('utf-8', errors='replace') if isinstance(raw_body, bytes) else (raw_body or '')
        expected = hashlib.sha256(
            ('%s%s%s%s' % (self.config.zalo_app_id or '', body, timestamp, secret)).encode('utf-8')
        ).hexdigest()
        return bool(provided) and hmac.compare_digest(provided, expected)

    @staticmethod
    def parse(payload):
        """(sender_id, text) of a user text message, or ('', '')."""
        if not isinstance(payload, dict):
            return '', ''
        if payload.get('event_name') and payload['event_name'] != 'user_send_text':
            return '', ''
        message = payload.get('message') or {}
        sender = payload.get('sender') or {}
        text = (message.get('text') or '').strip() if isinstance(message, dict) else ''
        sender_id = str(sender.get('id') or '') if isinstance(sender, dict) else ''
        return sender_id, text

    def _send(self, user_id, text, token):
        res = _session().post(
            '%s/message/cs' % self.API, timeout=15,
            headers={'Content-Type': 'application/json', 'access_token': token},
            data=json.dumps({'recipient': {'user_id': user_id}, 'message': {'text': text}}))
        try:
            return res.json()
        except ValueError:
            return {'error': res.status_code}

    def _refresh(self):
        cfg = self.config
        res = _session().post(
            self.OAUTH, timeout=15,
            headers={'secret_key': cfg.zalo_secret_key or '', 'Content-Type': 'application/x-www-form-urlencoded'},
            data={'app_id': cfg.zalo_app_id or '', 'grant_type': 'refresh_token',
                  'refresh_token': cfg.zalo_refresh_token or ''})
        data = res.json()
        if data.get('access_token'):
            # Zalo refresh tokens are single-use: the new one must be kept
            cfg.write({'zalo_access_token': data['access_token'],
                       'zalo_refresh_token': data.get('refresh_token') or cfg.zalo_refresh_token})
        return data.get('access_token') or ''

    def send_text(self, user_id, text):
        """'' on success, otherwise a short error for the webhook log."""
        if not (self.config.zalo_access_token and user_id and text):
            return 'unconfigured'
        data = self._send(user_id, text, self.config.zalo_access_token)
        if data.get('error') == -216:
            token = self._refresh()
            if not token:
                return 'token refresh failed'
            data = self._send(user_id, text, token)
        return '' if data.get('error') in (0, None) else 'zalo error %s: %s' % (data.get('error'), data.get('message'))


class FacebookChannel:
    GRAPH = 'https://graph.facebook.com/v21.0'

    def __init__(self, config):
        self.config = config

    def verify_subscription(self, params):
        """The challenge Facebook expects back on a GET, or None."""
        mode = params.get('hub.mode') or params.get('hub_mode') or ''
        token = params.get('hub.verify_token') or params.get('hub_verify_token') or ''
        expected = self.config.facebook_verify_token or ''
        if mode == 'subscribe' and self.config.facebook_enabled and expected \
                and hmac.compare_digest(str(token), str(expected)):
            return params.get('hub.challenge') or params.get('hub_challenge') or ''
        return None

    def verify_signature(self, raw_body, signature_header):
        secret = self.config.facebook_app_secret or ''
        if not (signature_header and secret):
            return False
        provided = signature_header[7:] if signature_header.startswith('sha256=') else signature_header
        expected = hmac.new(secret.encode('utf-8'), raw_body or b'', hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided, expected)

    def iter_text_events(self, payload):
        """Yield (sender_id, text, mid) for each customer text message; skip echoes."""
        if not isinstance(payload, dict) or payload.get('object') != 'page':
            return
        page_id = str(self.config.facebook_page_id or '')
        for entry in payload.get('entry') or []:
            for ev in entry.get('messaging') or []:
                msg = ev.get('message') if isinstance(ev, dict) else None
                if not isinstance(msg, dict) or msg.get('is_echo'):
                    continue
                text = (msg.get('text') or '').strip()
                recipient = str((ev.get('recipient') or {}).get('id') or '')
                if not text or (page_id and recipient and recipient != page_id):
                    continue
                yield str((ev.get('sender') or {}).get('id') or ''), text, msg.get('mid')

    def _send(self, psid, text, token):
        try:
            res = _session(post_retries=True).post(
                '%s/me/messages' % self.GRAPH, timeout=15,
                headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % token},
                data=json.dumps({'recipient': {'id': psid}, 'messaging_type': 'RESPONSE',
                                 'message': {'text': text}}))
            data = res.json()
        except Exception as e:
            _logger.error("isd_ai_chatbot: Facebook send failed: %s", e)
            return 'error'
        if res.status_code == 200 and not data.get('error'):
            return ''
        return 'expired' if (data.get('error') or {}).get('code') == 190 else 'error: %s' % res.text[:200]

    def _refresh(self):
        cfg = self.config
        if not (cfg.facebook_app_id and cfg.facebook_app_secret and cfg.facebook_page_access_token):
            return ''
        try:
            data = _session().get('%s/oauth/access_token' % self.GRAPH, timeout=15, params={
                'grant_type': 'fb_exchange_token', 'client_id': cfg.facebook_app_id,
                'client_secret': cfg.facebook_app_secret,
                'fb_exchange_token': cfg.facebook_page_access_token}).json()
        except Exception as e:
            _logger.error("isd_ai_chatbot: Facebook token refresh failed: %s", e)
            return ''
        if data.get('access_token'):
            cfg.write({'facebook_page_access_token': data['access_token']})
        return data.get('access_token') or ''

    def send_text(self, psid, text):
        token = self.config.facebook_page_access_token
        if not (token and psid and text):
            return 'unconfigured'
        status = self._send(psid, text, token)
        if status == 'expired':
            new_token = self._refresh()
            status = self._send(psid, text, new_token) if new_token else 'expired'
        return status
