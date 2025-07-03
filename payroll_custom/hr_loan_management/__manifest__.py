{
    'name': 'Gestión de Préstamos a Empleados',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión completa de préstamos a empleados con integración a nómina',
    'description': """
        Módulo para gestionar préstamos a empleados con las siguientes características:
        
        Características principales:
        * Gestión completa de préstamos (crear, aprobar, procesar, completar)
        * Generación automática de cuotas mensuales
        * Integración automática con nómina para descuentos
        * Estados de flujo: Borrador → Aprobado → En Curso → Completado
        * Cálculo automático de saldo pendiente
        * Límite de 10 cuotas máximo por préstamo
        * Validaciones de fechas y montos
        * Seguimiento de pagos por nómina
        * Reportes y análisis de préstamos
        * Interfaz moderna con vistas Kanban
        
        Funcionalidades avanzadas:
        * Cálculo automático de cuotas
        * Validación de empleados activos
        * Control de préstamos simultáneos
        * Integración con estructura salarial
        * Manejo de diferentes monedas
        * Auditoría completa de transacciones
    """,
    'author': 'Luis E. Becerra S.',
    'website': 'https://github.com/Kowalsky98/',
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
