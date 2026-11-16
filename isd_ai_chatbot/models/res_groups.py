# -*- coding: utf-8 -*-
from odoo import api, models

CATEGORY = 'isd_ai_chatbot.module_category_ai_chatbot'
ROLES = ('group_guest', 'group_user', 'group_editor', 'group_manager', 'group_admin')


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def get_groups_by_application(self):
        """Show the chatbot roles as one dropdown, like isd_chatbot.

        Odoo offers a dropdown only for a straight ladder of roles. Here User
        and Editor are separate branches that Manager combines, so Odoo falls
        back to checkboxes. It makes the same exception for Accounting, where
        Auditor and Invoicing sit side by side under Accountant: pick one role,
        and the role's implied groups do the rest.
        """
        res = super().get_groups_by_application()
        category = self.env.ref(CATEGORY, raise_if_not_found=False)
        roles = self.browse()
        for xmlid in ROLES:
            roles |= self.env.ref('isd_ai_chatbot.%s' % xmlid, raise_if_not_found=False) or self.browse()
        out = []
        for app, kind, groups, category_name in res:
            # Only while the category holds exactly these roles: a group some
            # other module adds to it must not vanish into a dropdown
            if category and app == category and kind == 'boolean' and groups == roles:
                order = {g: len(g.trans_implied_ids & groups) for g in groups}
                ordered = groups.sorted(key=lambda g: (order[g], g.id))
                parent = app.parent_id
                name = (parent.sequence, parent.name) if parent else (100, 'Other')
                out.append((app, 'selection', ordered, name))
            else:
                out.append((app, kind, groups, category_name))
        return out
