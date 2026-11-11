# -*- coding: utf-8 -*-
{
    'name': 'AI Chatbot (by ISD)',
    'version': '18.0.1.0.0',
    'category': 'ISD Modules',
    'summary': 'AI chatbot that answers from your own documents, captures leads, and talks on Zalo and Messenger',
    'description': """
AI Chatbot (by ISD)
===================
* Answers from a knowledge base (Word files or typed text) and an approved Q&A table,
  through Gemini or OpenAI when a key is set, and from its own documents when not
* Captures leads in conversation: name, phone, email, topic and meeting time
* Leads: assign to a salesperson, push to CRM, book a meeting with a video link
* Full conversation history, for the website, Zalo OA and Facebook Messenger
* Embeddable widget for any website: chat plus phone, Zalo and Messenger buttons
* REST API for leads
    """,
    'author': 'IntelliSyncData',
    'website': 'https://intellisyncdata.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'website', 'mail', 'crm', 'calendar'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'data/source_data.xml',
        'data/cron.xml',
        'data/mail_templates.xml',
        'views/config_views.xml',
        'views/knowledge_views.xml',
        'views/qa_views.xml',
        'views/lead_views.xml',
        'views/conversation_views.xml',
        'views/source_views.xml',
        'views/webhook_log_views.xml',
        'views/res_users_views.xml',
        'views/website_templates.xml',
        'wizard/assign_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
