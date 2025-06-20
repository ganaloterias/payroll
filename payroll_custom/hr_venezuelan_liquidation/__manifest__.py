# -*- coding: utf-8 -*-
{
    'name': 'Liquidaciones Venezuela',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión de liquidaciones según la ley venezolana',
    'description': """
        Módulo para gestionar las liquidaciones de empleados según la ley venezolana.
        Incluye:
        * Cálculo de liquidaciones
        * Generación de reportes
        * Integración con nómina
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'hr',
        'payroll',
        'hr_contract',
        'hr_holidays',
    ],
    'data': [
        'security/liquidation_security.xml',
        'security/ir.model.access.csv',
        'wizard/liquidation_wizard_view.xml',
        'wizard/liquidation_payment_wizard_view.xml',
        'views/liquidation_views.xml',
        'views/liquidation_menu.xml',
        'report/liquidation_report.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
