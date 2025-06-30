# -*- coding: utf-8 -*-
{
    'name': 'Pago de Vacaciones Venezuela',
    'version': '18.0.2.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión completa de pagos de vacaciones según LOTTT con integración a nómina',
    'description': """
        Módulo para gestionar el pago de vacaciones según la Ley Orgánica del Trabajo, 
        los Trabajadores y las Trabajadoras (LOTTT) de Venezuela.
        
        Características principales:
        * Cálculo automático de días de vacaciones según años de servicio
        * Cálculo de bono vacacional según antigüedad
        * Generación automática de ausencias por vacaciones
        * Integración completa con nómina para inputs automáticos
        * Validaciones según ley venezolana
        * Reportes personalizados
        * Gestión de estados: Borrador → Validado → Pagado → Rechazado
        * Vista de calendario para visualización temporal
        * Dashboard con gráficos y análisis
        
        Cálculos según LOTTT:
        * Días de vacaciones: 15 días mínimo, aumenta con la antigüedad
        * Bono vacacional: igual a los días de vacaciones
        * Factor de cálculo: salario diario = salario mensual / 30
        
        Fase 2 - Mejoras:
        * Integración automática con nómina
        * Inputs automáticos en nóminas
        * Vista de calendario mejorada
        * Dashboard con análisis
        * UX simplificada y mejorada
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_contract',
        'payroll',
        'hr_holidays',
        'mail',
        'base',
        'web',
    ],
    'data': [
        'security/vacation_security.xml',
        'security/ir.model.access.csv',
        'data/vacation_sequence.xml',
        'wizard/vacation_payout_wizard_view.xml',
        'views/vacation_views.xml',
        'views/vacation_menu.xml',
        'report/vacation_payout_report.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
