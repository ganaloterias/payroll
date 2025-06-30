{
    'name': 'Loan Management for Employees',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión completa de préstamos a empleados con integración a nómina',
    'description': """
        Módulo para gestionar préstamos a empleados con las siguientes características:
        * Gestión completa de préstamos (crear, aprobar, procesar, completar)
        * Generación automática de cuotas
        * Integración automática con nómina para descuentos
        * Estados de flujo: Borrador → Aprobado → En Curso → Completado
        * Cálculo automático de saldo pendiente
        * Límite de 10 cuotas máximo por préstamo
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': ['hr', 'payroll', 'base'],
    'data': [
        # Security first
        'security/hr_loan_security.xml',
        'security/ir.model.access.csv',
        # Data files
        'data/loan_sequence.xml',
        'data/loan_deduction_category.xml',
        'data/rule_inputs.xml',
        # Views
        'views/hr_loan_installment_views.xml',
        'views/hr_loan_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_payslip_tree_views.xml',
        'views/hr_payslip_run_tree_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
