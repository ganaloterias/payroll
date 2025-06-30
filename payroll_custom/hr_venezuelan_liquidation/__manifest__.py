# -*- coding: utf-8 -*-
{
    'name': 'Liquidaciones Venezuela',
    'version': '18.0.2.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión completa de liquidaciones según la ley venezolana con cálculos automáticos',
    'description': """
        Módulo para gestionar las liquidaciones de empleados según la Ley Orgánica del Trabajo, 
        los Trabajadores y las Trabajadoras (LOTTT) de Venezuela.
        
        Características principales:
        * Cálculo automático de liquidaciones según LOTTT
        * Gestión de prestaciones sociales, vacaciones y bono vacacional
        * Cálculo de preaviso según antigüedad
        * Integración completa con nómina para obtener último salario
        * Estados de flujo: Borrador → Validado → Finalizado → Cancelado
        * Secuencias automáticas y únicas
        * Validaciones según ley venezolana
        * Wizards para creación rápida y registro de pagos
        * Reportes personalizados
        * Vistas modernas (Lista, Formulario, Kanban, Gráficos, Pivot)
        * Auditoría completa con seguimiento de cambios
        * Integración con mensajería y actividades
        
        Cálculos incluidos según LOTTT:
        * Vacaciones no gozadas (15 días mínimo, aumenta con antigüedad)
        * Bono vacacional (igual a días de vacaciones)
        * Prestaciones sociales (método C y fondo de garantía)
        * Preaviso según antigüedad (7, 15 o 30 días)
        
        Mejoras en esta versión:
        * Optimización completa para Odoo 18
        * Mejores prácticas de desarrollo
        * Validaciones robustas
        * Interfaz de usuario mejorada
        * Integración perfecta con módulos HR y Payroll
        * Secuencias lógicas y únicas
        * Cálculos precisos según ley venezolana
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'hr',
        'payroll',
        'hr_contract',
        'hr_holidays',
        'mail',
        'base',
        'web',
    ],
    'data': [
        # Security first
        'security/liquidation_security.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data files
        'data/liquidation_sequence.xml',
        # Wizard views
        'wizard/liquidation_wizard_view.xml',
        'wizard/liquidation_payment_wizard_view.xml',
        # Main views
        'views/liquidation_views.xml',
        'views/liquidation_menu.xml',
        # Reports
        'report/liquidation_report.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            # Aquí se pueden agregar assets JS/CSS si es necesario
        ],
    },
}
