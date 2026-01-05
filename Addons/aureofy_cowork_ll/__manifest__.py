# -*- coding: utf-8 -*-
{
    'name': 'Aureofy-Cowork-LL',
    'version': '17.0.1.0.0',
    'category': 'Services',
    'summary': 'Sistema de Gestión de Espacios de Coworking y Coliving',
    'description': """
        Aureofy Cowork & Coliving Management System
        ============================================
        
        Sistema integral para gestionar espacios de coworking y coliving:
        
        * Gestión de membresías (diarias, mensuales, anuales)
        * Administración de escritorios y camas
        * Sistema de créditos para servicios adicionales
        * Solicitudes de acceso a instalaciones
        * Portal de miembros
        * Integración con CRM
        * Dashboard con estadísticas
        * Reportes PDF
        * Tarjetas de miembro con QR
        * Envío masivo de emails
    """,
    'author': 'Aureofy',
    'website': 'https://www.aureofy.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'crm',
        'account',
        'sale_management',
        'website',
        'portal',
        'contacts',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequence_data.xml',
        'data/mail_template_data.xml',
        
        # Views
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        'views/cowork_floor_views.xml',
        'views/cowork_desk_views.xml',
        'views/cowork_bed_views.xml',
        'views/cowork_service_views.xml',
        'views/cowork_policy_views.xml',
        'views/cowork_tag_views.xml',
        'views/cowork_membership_plan_views.xml',
        'views/cowork_membership_views.xml',
        'views/cowork_access_request_views.xml',
        'views/cowork_security_deposit_views.xml',
        'views/cowork_rating_views.xml',
        'views/cowork_credits_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        
        # Wizards
        'wizard/mass_mail_wizard_views.xml',
        'wizard/member_card_wizard_views.xml',
        
        # Reports
        'report/membership_report.xml',
        'report/member_card_report.xml',
        
        # Website & Portal
        'views/website_templates.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'aureofy_cowork_ll/static/src/css/style.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
