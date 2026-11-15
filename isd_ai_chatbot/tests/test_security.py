# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

MENUS = ('menu_root', 'menu_leads', 'menu_conversations', 'menu_content', 'menu_knowledge', 'menu_qa',
         'menu_configuration', 'menu_settings', 'menu_sources', 'menu_webhook_logs')


@tagged('post_install', '-at_install')
class TestRoles(TransactionCase):
    """Roles as in isd_chatbot: who sees which menu."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def user(login, group):
            groups = 'base.group_user' + (',isd_ai_chatbot.%s' % group if group else '')
            return new_test_user(cls.env, login=login, groups=groups)
        cls.users = {role: user('aic_%s' % role, group) for role, group in (
            ('none', None), ('guest', 'group_guest'), ('user', 'group_user'), ('editor', 'group_editor'),
            ('manager', 'group_manager'), ('admin', 'group_admin'))}

    def _menus(self, role):
        visible = self.env['ir.ui.menu'].with_user(self.users[role])._visible_menu_ids()
        return {name for name in MENUS if self.env.ref('isd_ai_chatbot.%s' % name).id in visible}

    def test_menus_per_role(self):
        expected = {
            'none': set(),
            'guest': set(),
            'user': {'menu_root', 'menu_leads', 'menu_conversations'},
            'editor': {'menu_root', 'menu_content', 'menu_knowledge', 'menu_qa'},
            'manager': {'menu_root', 'menu_leads', 'menu_conversations', 'menu_content', 'menu_knowledge', 'menu_qa'},
            'admin': set(MENUS),
        }
        for role, menus in expected.items():
            self.assertEqual(self._menus(role), menus, role)

    def test_data_per_role(self):
        Lead = self.env['isd.ai.chatbot.lead']
        mine = Lead.create({'name': 'Mine', 'phone': '0901000001', 'assigned_user_id': self.users['user'].id})
        other = Lead.create({'name': 'Other', 'phone': '0901000002', 'assigned_user_id': self.users['admin'].id})
        # A user sees only the leads assigned to them; a manager sees all
        self.assertEqual(Lead.with_user(self.users['user']).search([('id', 'in', (mine | other).ids)]), mine)
        self.assertEqual(Lead.with_user(self.users['manager']).search([('id', 'in', (mine | other).ids)]), mine | other)
        # An editor keeps the answers up to date and sees no leads
        with self.assertRaises(AccessError):
            Lead.with_user(self.users['editor']).search([])
        self.env['isd.ai.chatbot.qa'].with_user(self.users['editor']).create({'name': 'Q', 'keywords': 'q'})
        for role in ('guest', 'user'):
            with self.assertRaises(AccessError):
                self.env['isd.ai.chatbot.qa'].with_user(self.users[role]).search([])
        # Only an admin may change the settings
        config = self.env['isd.ai.chatbot.config'].get_config()
        with self.assertRaises(AccessError):
            config.with_user(self.users['manager']).write({'bot_title': 'x'})
        config.with_user(self.users['admin']).write({'bot_title': 'x'})
