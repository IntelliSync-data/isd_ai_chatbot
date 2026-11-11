# -*- coding: utf-8 -*-
import secrets

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError

from . import sample_data

DEFAULT_COLOR = '#0b53cb'


class IsdAiChatbotConfig(models.Model):
    """The one configuration record. Kept on a model rather than in
    ir.config_parameter so secrets sit behind a group, not in a table every
    administrator screen reads."""
    _name = 'isd.ai.chatbot.config'
    _description = 'AI Chatbot Settings'

    name = fields.Char(default='AI Chatbot', required=True)

    # Who the bot speaks for
    business_name = fields.Char(string='Business Name', help='Defaults to the company name')
    business_website = fields.Char(string='Business Website')
    bot_title = fields.Char(string='Bot Name', default='AI Assistant')
    bot_subtitle = fields.Char(string='Bot Subtitle', default='Customer support · 24/7')

    # Words the customer reads, one per language
    greeting_vi = fields.Char(string='Bubble Greeting (VI)',
                              default='Chào bạn! 👋 Cần hỗ trợ gì cứ nhắn cho mình nhé!')
    greeting_en = fields.Char(string='Bubble Greeting (EN)',
                              default='Hi there! 👋 Message us if you need anything.')
    welcome_message_vi = fields.Text(string='Welcome Message (VI)',
                                     default='Xin chào! Mình có thể giúp gì cho bạn?')
    welcome_message_en = fields.Text(string='Welcome Message (EN)', default='Hello! How can I help you?')
    fallback_message_vi = fields.Text(
        string='No-Answer Message (VI)',
        default=('Dạ mình chưa có thông tin cho câu hỏi này ạ. Bạn bấm **Nói chuyện với người thật** '
                 'để chuyên viên hỗ trợ trực tiếp nhé!'))
    fallback_message_en = fields.Text(
        string='No-Answer Message (EN)',
        default="I don't have an answer for that yet. Tap **Talk to a person** and our team will help you directly.")
    suggested_questions_vi = fields.Text(string='Suggested Questions (VI)', help='One per line')
    suggested_questions_en = fields.Text(string='Suggested Questions (EN)', help='One per line')

    # How the language model should speak
    pronoun_style = fields.Char(string='Form of Address (VI)', default='Xưng "mình", gọi khách là "bạn"')
    tone_instruction = fields.Text(string='Tone', default='Warm, clear and concise. 3-4 short sentences.')
    core_philosophy = fields.Text(string='Key Message')
    forbidden_claims = fields.Text(string='Never Say')
    handoff_rule = fields.Text(string='Hand-over Rule',
                               default='When the customer asks for a person, or the material does not cover the question.')
    query_expansions = fields.Text(
        string='Query Expansions',
        help='One rule per line: "price, cost, how much => gia ban uu dai". Lets an English '
             'question find a Vietnamese document, and the other way round.')

    # Language models
    gemini_api_key = fields.Char(string='Gemini API Key', groups='isd_ai_chatbot.group_admin')
    gemini_model = fields.Char(string='Gemini Model', default='gemini-2.5-flash')
    openai_api_key = fields.Char(string='OpenAI API Key', groups='isd_ai_chatbot.group_admin')
    openai_model = fields.Char(string='OpenAI Model', default='gpt-4o-mini')
    has_language_model = fields.Boolean(compute='_compute_has_language_model')

    # Look of the chat window
    primary_color = fields.Char(string='Primary Color', default=DEFAULT_COLOR)
    secondary_color = fields.Char(string='Secondary Color', default='#1d4ed8')
    avatar = fields.Image(string='Bot Avatar', max_width=256, max_height=256)

    # Where the bubble appears, and what it opens
    website_ids = fields.Many2many(
        'website', string='Show on Websites',
        help='Odoo websites that show the chat bubble on every page. Pages outside Odoo use the embed code.')
    cors_origins = fields.Text(
        string='Allowed Domains',
        help='One per line, e.g. https://shop.example.com. Empty means any site may embed the widget.')
    show_chat_button = fields.Boolean(string='Chat Button', default=True)
    phone = fields.Char(string='Phone Number', help='Shows a call button, e.g. +84901234567')
    zalo_link = fields.Char(string='Zalo Link', help='Shows a Zalo button, e.g. https://zalo.me/0901234567')
    messenger_link = fields.Char(string='Messenger Link', help='Shows a Messenger button, e.g. https://m.me/yourpage')
    color_toggle = fields.Char(string='Toggle Button Color', default=DEFAULT_COLOR)
    color_chat = fields.Char(string='Chat Button Color', default=DEFAULT_COLOR)
    color_phone = fields.Char(string='Phone Button Color', default='#16a34a')
    color_zalo = fields.Char(string='Zalo Button Color', default='#0068ff')
    color_messenger = fields.Char(string='Messenger Button Color', default='#a334fa')
    icon_toggle = fields.Image(string='Toggle Icon', max_width=128, max_height=128)
    icon_chat = fields.Image(string='Chat Icon', max_width=128, max_height=128)
    icon_phone = fields.Image(string='Phone Icon', max_width=128, max_height=128)
    icon_zalo = fields.Image(string='Zalo Icon', max_width=128, max_height=128)
    icon_messenger = fields.Image(string='Messenger Icon', max_width=128, max_height=128)
    embed_code = fields.Char(string='Embed Code', compute='_compute_embed_code')

    # Leads
    auto_assign = fields.Boolean(
        string='Assign Leads Automatically', default=True,
        help='Round-robin between users marked as chatbot agents (Settings > Users)')
    auto_crm = fields.Boolean(string='Create CRM Lead Automatically',
                              help='Push every new lead to CRM as soon as the bot captures it')
    timezone = fields.Selection(_tz_get, string='Customer Timezone', default='Asia/Ho_Chi_Minh',
                                help='Dates customers type in the chat are read in this timezone')
    hide_analyze_button = fields.Boolean(string='Hide "Analyze"')
    hide_crm_button = fields.Boolean(string='Hide "Save to CRM"')

    # Zalo OA
    zalo_enabled = fields.Boolean(string='Zalo Enabled')
    zalo_app_id = fields.Char(string='Zalo App ID', groups='isd_ai_chatbot.group_admin')
    zalo_secret_key = fields.Char(string='Zalo App Secret Key', groups='isd_ai_chatbot.group_admin')
    zalo_access_token = fields.Text(string='Zalo Access Token', groups='isd_ai_chatbot.group_admin')
    zalo_refresh_token = fields.Text(string='Zalo Refresh Token', groups='isd_ai_chatbot.group_admin')
    zalo_webhook_secret = fields.Char(
        string='Zalo OA Secret Key (webhook)', groups='isd_ai_chatbot.group_admin',
        help='From the OA webhook settings. When set, events without a valid X-ZEvent-Signature are refused.')

    # Facebook Messenger
    facebook_enabled = fields.Boolean(string='Facebook Enabled')
    facebook_page_id = fields.Char(string='Page ID', groups='isd_ai_chatbot.group_admin')
    facebook_page_access_token = fields.Char(string='Page Access Token', groups='isd_ai_chatbot.group_admin')
    facebook_app_id = fields.Char(string='App ID', groups='isd_ai_chatbot.group_admin')
    facebook_app_secret = fields.Char(string='App Secret', groups='isd_ai_chatbot.group_admin')
    facebook_verify_token = fields.Char(string='Verify Token', groups='isd_ai_chatbot.group_admin')

    webhook_url_zalo = fields.Char(string='Zalo Webhook URL', compute='_compute_webhook_urls')
    webhook_url_facebook = fields.Char(string='Facebook Webhook URL', compute='_compute_webhook_urls')

    # REST API
    api_key = fields.Char(string='API Key', groups='isd_ai_chatbot.group_admin', copy=False,
                          help='Required by the REST API to read, change or delete leads. Creating one needs no key.')

    @api.model
    def get_config(self):
        """The configuration record, created on first use."""
        config = self.env.ref('isd_ai_chatbot.config_default', raise_if_not_found=False)
        if not config:
            config = self.sudo().search([], limit=1) or self.sudo().create({})
        return config

    def _compute_has_language_model(self):
        for rec in self:
            rec.has_language_model = bool(
                (rec.sudo().gemini_api_key or '').strip() or (rec.sudo().openai_api_key or '').strip())

    def _compute_embed_code(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.embed_code = '<script src="%s/isd_ai_chatbot/widget.js" defer></script>' % base

    def _compute_webhook_urls(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.webhook_url_zalo = '%s/isd_ai_chatbot/webhook?merchant=zalo' % base
            rec.webhook_url_facebook = '%s/isd_ai_chatbot/webhook?merchant=facebook' % base

    # ------------------------------------------------------------ text access
    def _text(self, field, lang):
        """A customer-facing text in the language asked, falling back to the other."""
        self.ensure_one()
        primary = getattr(self, '%s_%s' % (field, 'en' if lang == 'en' else 'vi'), '') or ''
        other = getattr(self, '%s_%s' % (field, 'vi' if lang == 'en' else 'en'), '') or ''
        return primary or other

    def _suggested_questions(self, lang):
        return [q.strip() for q in self._text('suggested_questions', lang).splitlines() if q.strip()][:8]

    def _allowed_origins(self):
        return [o.strip().rstrip('/') for o in (self.cors_origins or '').splitlines() if o.strip()]

    # ---------------------------------------------------------------- buttons
    def action_generate_api_key(self):
        self.ensure_one()
        self.api_key = secrets.token_urlsafe(32)

    def action_load_sample_data(self):
        """Fill the knowledge base and Q&A with the Bloompod examples.

        A button rather than data files: a generic module must not install one
        customer's prices and hotline on every database it lands on.
        """
        self.ensure_one()
        created = sample_data.load(self.env, self)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'type': 'success', 'sticky': False,
                       'message': _('Sample loaded: %(qa)s Q&A entries, %(docs)s documents.') % created},
        }

    def write(self, vals):
        res = super().write(vals)
        if 'website_ids' in vals:
            # Odoo caches the rendered <head> of every website page, and the
            # bubble's script tag is in it. Without this, a site switched on
            # keeps showing pages without the bubble until the server restarts,
            # and one switched off keeps showing it.
            self.env.registry.clear_cache('templates')
        return res

    def unlink(self):
        if self.env.ref('isd_ai_chatbot.config_default', raise_if_not_found=False) in self:
            raise UserError(_('The chatbot settings cannot be deleted.'))
        return super().unlink()
