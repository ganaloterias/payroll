{
    'name': 'HR Contract Custom - Multimoneda',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Contracts',
    'summary': 'Soporte multimoneda avanzado para contratos de empleados',
    'description': """
        Módulo para gestión avanzada de contratos con soporte multimoneda:
        
        Características principales:
        * Múltiples líneas de salario por contrato
        * Soporte completo multimoneda
        * Gestión de fechas de vigencia
        * Selección automática de salario por moneda
        * Histórico de cambios salariales
        * Integración con nómina y otros módulos
        
        Fases de implementación:
        * Fase 1: Modelo y estructura base
        * Fase 2: Selección automática de salario
        * Fase 3: Integración con otros módulos
        * Fase 4: Validaciones y mejoras
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base', 
        'hr', 
        'hr_contract',
        'payroll',
    ],
    'data': [
        # Security first
        'security/contract_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/contract_sequence.xml',
        # Views
        'views/hr_contract_salary_line_views.xml',
        'views/hr_contract_views.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 