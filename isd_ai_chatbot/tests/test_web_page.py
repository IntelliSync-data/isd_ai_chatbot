# -*- coding: utf-8 -*-
import socket
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..services import web_page

PAGE = '''<html><head><title>Shop</title><style>p{}</style></head><body>
<nav><a>Home</a><a>About</a></nav>
<h1>Bang
    gia</h1>
<p>Goi co ban
   990.000d</p>
<h2>Lien he<br>Hotline</h2>
<div>Goi 0901 234 567 de duoc tu van tan tinh ve san pham va dich vu.</div>
<table><tr><th>Goi</th><th>Gia</th></tr><tr><td>Pro</td><td>1.990.000d</td></tr></table>
<script>var x = 1;</script>
</body></html>'''.encode()


def _resolve(ip):
    return lambda host, port, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]


class _Resp:
    def __init__(self, status=200, body=PAGE, location=None, ctype='text/html; charset=utf-8'):
        self.status_code = status
        self.is_redirect = location is not None
        self.headers = {'Content-Type': ctype}
        if location:
            self.headers['Location'] = location
        self._body = body

    def iter_content(self, size):
        yield self._body

    def close(self):
        pass


@tagged('post_install', '-at_install')
class TestWebPage(TransactionCase):

    def test_page_to_text(self):
        title, text = web_page.html_to_text(PAGE, 'utf-8')
        self.assertEqual(title, 'Shop')
        self.assertIn('## Bang gia\nGoi co ban 990.000d', text, 'source line breaks are not text')
        self.assertIn('## Lien he Hotline', text, 'a heading wrapped with <br> stays one heading')
        self.assertIn('Pro | 1.990.000d', text)
        self.assertNotIn('Home', text, 'the menu is not knowledge')
        self.assertNotIn('var x', text)

    def test_internal_addresses_refused(self):
        for ip in ('127.0.0.1', '10.0.0.5', '192.168.1.10', '169.254.169.254', '::1'):
            with patch.object(web_page.socket, 'getaddrinfo', _resolve(ip)), \
                    patch.object(web_page.requests, 'get') as get:
                with self.assertRaises(web_page.FetchError) as ctx:
                    web_page.fetch('http://looks-public.example')
                self.assertEqual(ctx.exception.code, 'internal')
                get.assert_not_called()

    def test_redirect_to_internal_refused(self):
        # A public page that redirects to the cloud metadata address
        def resolve(host, port, *a, **k):
            ip = '93.184.216.34' if host == 'public.example' else '169.254.169.254'
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
        with patch.object(web_page.socket, 'getaddrinfo', resolve), \
                patch.object(web_page.requests, 'get',
                             return_value=_Resp(302, location='http://metadata.internal/latest')) as get:
            with self.assertRaises(web_page.FetchError) as ctx:
                web_page.fetch('http://public.example')
        self.assertEqual(ctx.exception.code, 'internal')
        self.assertEqual(get.call_count, 1)

    def test_fetch_fills_document(self):
        with patch.object(web_page.socket, 'getaddrinfo', _resolve('93.184.216.34')), \
                patch.object(web_page.requests, 'get', return_value=_Resp()):
            doc = self.env['isd.ai.chatbot.knowledge'].create({'name': 'x', 'source_url': 'https://shop.example'})
            doc.name = False
            result = doc.action_fetch_url()
        self.assertEqual(result['params']['type'], 'success')
        self.assertEqual(doc.name, 'Shop')
        self.assertEqual(doc.source_type, 'website')
        self.assertTrue(doc.last_fetched)
        self.assertIn('## Bang gia', doc.content)

    def test_failure_is_kept_on_the_document(self):
        with patch.object(web_page.socket, 'getaddrinfo', _resolve('93.184.216.34')), \
                patch.object(web_page.requests, 'get', return_value=_Resp(ctype='application/pdf')):
            doc = self.env['isd.ai.chatbot.knowledge'].create({
                'name': 'x', 'source_url': 'https://shop.example/a.pdf', 'content': 'kept'})
            result = doc.action_fetch_url()
        self.assertEqual(result['params']['type'], 'danger')
        self.assertIn('application/pdf', doc.fetch_error)
        self.assertEqual(doc.content, 'kept')
