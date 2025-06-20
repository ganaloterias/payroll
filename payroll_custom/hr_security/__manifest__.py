# -*- coding: utf-8 -*-
{
    'name': 'HR Security',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Control de acceso para módulos de RRHH',
    'description': """
        Este módulo proporciona control de acceso para los módulos de RRHH,
        específicamente para empleados y ausencias.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr', 'hr_holidays'],
    'data': [
        'security/hr_security.xml',
        'views/hr_security_views.xml',
    ],
    'assets': {
              'web.assets_backend': [
                  'hr_security/static/src/**/*'
              ],
          },
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
