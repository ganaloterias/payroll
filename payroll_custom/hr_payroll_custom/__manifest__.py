{
    'name': 'Custom Payroll Enhancements',
    'version': '18.0.1.0.0',
    'summary': 'Mejoras personalizadas para nómina con optimizaciones de rendimiento',
    'description': """
        Extensiones optimizadas a la nómina con las siguientes características:
        * Generación masiva de archivos TXT para nómina con validaciones previas
        * Extensiones de datos bancarios para Venezuela
        * Gestión de dependientes de empleados
        * Cálculos optimizados de días trabajados y ausencias
        * Integración con módulos de préstamos y vacaciones
        * Soporte completo para contratos multimoneda
        * Validación automática de contratos según moneda
        * Wizard de migración de contratos existentes
        * Mejoras de rendimiento y arquitectura
        * Validaciones robustas y manejo de errores
    """,
    'category': 'Human Resources/Payroll',
    'author': 'Luis E. Becerra S.',
    'website': 'https://tusitio.com',
    'depends': [
        'base', 
        'payroll', 
        'hr', 
        'hr_contract',
        'hr_loan_management',  # Integración con préstamos
        'hr_vacation_payout',  # Integración con vacaciones
        'hr_contract_custom',  # Integración con contratos multimoneda
    ],
    'data': [
        # Security first
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/hr_employee_dependent_data.xml',
        'data/payroll_contract_config.xml',
        'data/contract_access_data.xml',
        # Views
        'views/res_partner_bank_view.xml',
        'views/hr_employee_views.xml',
        'views/partner_extended_views.xml',
        'views/payslip_actions.xml',
        'views/payslip_report_views.xml',
        'views/payslip_contract_views.xml',
        # Wizards
        'wizard/generate_txt_mass_wizard_view.xml',
        'wizard/contract_migration_wizard_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
