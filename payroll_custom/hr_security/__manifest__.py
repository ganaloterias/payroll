# -*- coding: utf-8 -*-
{
    'name': 'HR Security Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Security',
    'summary': 'Control de acceso avanzado para módulos de RRHH',
    'description': """
        Módulo de seguridad avanzado para controlar el acceso a módulos de RRHH:
        
        Características principales:
        * Control granular de acceso por módulo
        * Grupos de seguridad específicos para cada funcionalidad
        * Reglas de acceso personalizadas
        * Gestión de permisos por roles
        * Auditoría de acceso
        
        Módulos cubiertos:
        * Empleados y contratos
        * Nómina y pagos
        * Ausencias y vacaciones
        * Préstamos a empleados
        * Liquidaciones
        * Reportes y análisis
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base', 
        'hr', 
        'hr_holidays',
    ],
    'data': [
        # Security first
        'security/hr_security.xml',
        # Views
        'views/hr_security_views.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
