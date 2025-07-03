# -*- coding: utf-8 -*-
{
    'name': 'Gestión Avanzada de Nómina',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión avanzada de nómina y configuración para Venezuela',
    'description': """
        Módulo de configuración y gestión avanzada de nómina para Venezuela.
        
        Características principales:
        * Configuración centralizada de módulos de nómina
        * Gestión de parámetros de validación
        * Control de límites y restricciones
        * Configuración de reportes y notificaciones
        * Integración con módulos de contabilidad
        * Configuración de auditoría y logs
        
        Funcionalidades de configuración:
        * Activación/desactivación de módulos
        * Configuración de monedas principales
        * Validación de datos bancarios
        * Control de límites de préstamos
        * Configuración de reportes
        * Gestión de notificaciones por email
        * Configuración de auditoría
        * Integración con contabilidad
        
        Módulos gestionados:
        * Gestión de préstamos
        * Pago de vacaciones
        * Liquidaciones venezolanas
        * Seguridad avanzada
        * Mejoras personalizadas
    """,
    'author': 'Luis E. Becerra S.',
    'website': 'https://github.com/Kowalsky98/',
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
