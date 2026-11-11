# -*- coding: utf-8 -*-
{
    'name': 'AI Chatbot: OpenEduCat bridge (by ISD)',
    'version': '18.0.1.0.0',
    'category': 'ISD Modules',
    'summary': 'Invite a chatbot lead as a student, with a pre-filled survey',
    'description': """
Adds "Invite as Student" to AI Chatbot leads: creates the OpenEduCat student and
their portal login, sends the invitation, and starts a survey with the answers
the lead already gave.

Installs itself on a database that has both AI Chatbot and OpenEduCat, and
never on one that lacks either - which is what keeps AI Chatbot installable
on sites without OpenEduCat.
    """,
    'author': 'IntelliSyncData',
    'website': 'https://intellisyncdata.com',
    'license': 'LGPL-3',
    'depends': ['isd_ai_chatbot', 'survey', 'openeducat_core'],
    'data': [
        'security/ir.model.access.csv',
        'views/survey_mapping_views.xml',
        'views/lead_views.xml',
    ],
    'auto_install': True,
    'installable': True,
}
