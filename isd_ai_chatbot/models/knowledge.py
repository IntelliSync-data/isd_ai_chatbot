# -*- coding: utf-8 -*-
import base64
import html
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET

from odoo import api, fields, models

_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _docx_to_text(raw):
    """Paragraphs of a .docx, with Word headings turned into '## '.

    The search splits documents on '## ' lines. chatbot_ai_rag stripped the
    XML tags and lost the headings, so a well-structured Word file reached the
    search as one long block and answers could not point at the right section.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        root = ET.fromstring(zf.read('word/document.xml'))
        styles = ET.fromstring(zf.read('word/styles.xml')) if 'word/styles.xml' in zf.namelist() else None

    # A style id is localised (a German Word writes "berschrift1"), but the
    # name of a built-in style is always stored in English: "heading 1".
    heading_ids = set()
    if styles is not None:
        for st in styles.iter('%sstyle' % _W):
            name = st.find('%sname' % _W)
            if name is not None and re.match(r'^(heading \d|title)$', (name.get('%sval' % _W) or '').lower()):
                heading_ids.add(st.get('%sstyleId' % _W))
    lines = []
    for p in root.iter('%sp' % _W):
        style = p.find('%spPr/%spStyle' % (_W, _W))
        style_name = (style.get('%sval' % _W) or '') if style is not None else ''
        parts = []
        for node in p.iter():
            if node.tag == '%st' % _W and node.text:
                parts.append(node.text)
            elif node.tag == '%stab' % _W:
                parts.append('\t')
            elif node.tag == '%sbr' % _W:
                parts.append('\n')
        text = ''.join(parts).strip()
        if not text:
            continue
        if style_name in heading_ids or re.match(r'^(heading\s*\d|title)$', style_name, re.I):
            lines.append('')
            lines.append('## %s' % text)
        else:
            lines.append(text)
    return '\n'.join(lines).strip()


def extract_text(raw, filename=''):
    ext = os.path.splitext((filename or '').lower())[1]
    if ext == '.docx' or raw[:4] == b'PK\x03\x04':
        try:
            return _docx_to_text(raw)
        except Exception:
            pass
    # Old binary .doc: no parser in the standard library, so take the runs of
    # readable UTF-16 text. Rough, and better than nothing; .docx is preferred.
    if raw[:4] == b'\xd0\xcf\x11\xe0':
        utf16 = raw.decode('utf-16le', errors='ignore')
        runs = [r.strip() for r in re.findall(r'[\w\s.,;:!?()"\'\-–—/+%•*#@&\n\r]{15,}', utf16, flags=re.U)]
        runs = [r for r in runs if len(r) >= 15 and not re.match(
            r'^(Root Entry|WordDocument|SummaryInformation|DocumentSummaryInformation|Normal\.dotm?|Microsoft Office Word)',
            r, re.I)]
        if runs:
            return '\n'.join(runs)
    text = raw.decode('utf-8', errors='ignore')
    return html.unescape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)).strip()


class IsdAiChatbotKnowledge(models.Model):
    _name = 'isd.ai.chatbot.knowledge'
    _description = 'AI Chatbot Knowledge Document'
    _order = 'sequence, id desc'

    name = fields.Char(string='Title', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    source_type = fields.Selection([
        ('website', 'Website'),
        ('docx', 'Word (.docx)'),
        ('doc', 'Word (.doc)'),
        ('manual', 'Typed in'),
    ], string='Source', default='manual', required=True)
    category = fields.Char()
    source_url = fields.Char(string='Source URL')
    upload_file = fields.Binary(string='File', attachment=True,
                                help='A .docx, .doc or .txt file. Its text is copied into Content.')
    upload_filename = fields.Char(string='File Name')
    content = fields.Text(help='Start each section with "## " on its own line, so answers can cite the right part.')
    summary = fields.Char(compute='_compute_summary', store=True)
    char_count = fields.Integer(string='Characters', compute='_compute_summary', store=True)

    @api.depends('content')
    def _compute_summary(self):
        for rec in self:
            clean = re.sub(r'\s+', ' ', (rec.content or '').strip())
            rec.summary = (clean[:180] + '...') if len(clean) > 180 else clean
            rec.char_count = len(rec.content or '')

    def _source_type_for(self, filename):
        ext = os.path.splitext((filename or '').lower())[1]
        return {'.docx': 'docx', '.doc': 'doc'}.get(ext)

    @api.onchange('upload_file', 'upload_filename')
    def _onchange_upload_file(self):
        for rec in self:
            if not rec.upload_file:
                continue
            text = extract_text(base64.b64decode(rec.upload_file), rec.upload_filename or '')
            if text:
                rec.content = text
            rec.source_type = self._source_type_for(rec.upload_filename) or rec.source_type
            if not rec.name and rec.upload_filename:
                rec.name = os.path.splitext(rec.upload_filename)[0]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('upload_file') and not vals.get('content'):
                vals['content'] = extract_text(base64.b64decode(vals['upload_file']), vals.get('upload_filename', ''))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('upload_file') and not vals.get('content'):
            filename = vals.get('upload_filename') or (self[:1].upload_filename or '')
            vals['content'] = extract_text(base64.b64decode(vals['upload_file']), filename)
        return super().write(vals)
