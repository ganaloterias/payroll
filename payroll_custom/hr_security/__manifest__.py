# -*- coding: utf-8 -*-
{
    'name': 'Gestión de Seguridad de RRHH',
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
        * Auditoría de acceso y cambios
        * Protección de datos sensibles
        
        Módulos cubiertos:
        * Empleados y contratos
        * Nómina y pagos
        * Ausencias y vacaciones
        * Préstamos a empleados
        * Liquidaciones
        * Reportes y análisis
        
        Funcionalidades de seguridad:
        * Control de acceso por niveles
        * Validación de permisos en tiempo real
        * Registro de actividades de usuarios
        * Protección contra acceso no autorizado
        * Configuración flexible de roles
        * Integración con sistema de autenticación
    """,
    'author': 'Luis E. Becerra S.',
    'website': 'https://github.com/Kowalsky98/',
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
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
