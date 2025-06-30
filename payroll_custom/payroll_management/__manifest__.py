# -*- coding: utf-8 -*-
{
    'name': 'Payroll Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión avanzada de nómina y configuración',
    'description': """
        Módulo de configuración y gestión avanzada de nómina para Venezuela.
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base',
        'payroll',
        'hr',
        'hr_contract',
    ],
    'data': [
        'security/payroll_security.xml',
        'views/payroll_menus_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
