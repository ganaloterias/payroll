from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuración de módulos
    module_hr_loan_management = fields.Boolean(
        string="Gestión de Préstamos a Empleados",
        help="Instala el módulo de gestión de préstamos (hr_loan_management)."
    )
    module_hr_vacation_payout = fields.Boolean(
        string="Gestión de Pago de Vacaciones",
        help="Instala el módulo para el pago de vacaciones (hr_vacation_payout)."
    )
    module_hr_venezuelan_liquidation = fields.Boolean(
        string="Gestión de Liquidaciones (Venezuela)",
        help="Instala el módulo para liquidaciones según la ley venezolana (hr_venezuelan_liquidation)."
    )
    module_hr_security = fields.Boolean(
        string="Seguridad Avanzada de RRHH",
        help="Instala el módulo de seguridad de RRHH (hr_security)."
    )
    
    # Configuración de nómina
    payroll_currency_id = fields.Many2one(
        'res.currency',
        string="Moneda Principal de Nómina",
        help="Moneda principal para cálculos de nómina",
        default=lambda self: self.env.company.currency_id
    )
    
    payroll_company_id = fields.Many2one(
        'res.company',
        string="Compañía de Nómina",
        help="Compañía principal para gestión de nómina",
        default=lambda self: self.env.company
    )
    
    # Configuración de validaciones
    validate_bank_accounts = fields.Boolean(
        string="Validar Cuentas Bancarias",
        help="Validar que los empleados tengan cuentas bancarias válidas",
        default=True
    )
    
    validate_identification = fields.Boolean(
        string="Validar Identificación",
        help="Validar que los empleados tengan identificación válida",
        default=True
    )
    
    # Configuración de límites
    max_loan_installments = fields.Integer(
        string="Máximo de Cuotas de Préstamo",
        help="Número máximo de cuotas permitidas para préstamos",
        default=10
    )
    
    max_txt_payslips = fields.Integer(
        string="Máximo de Nóminas en TXT",
        help="Número máximo de nóminas a procesar en archivo TXT",
        default=1000
    )
    
    # Configuración de reportes
    enable_payroll_reports = fields.Boolean(
        string="Habilitar Reportes de Nómina",
        help="Habilitar reportes personalizados de nómina",
        default=True
    )
    
    enable_loan_reports = fields.Boolean(
        string="Habilitar Reportes de Préstamos",
        help="Habilitar reportes de préstamos",
        default=True
    )
    
    enable_vacation_reports = fields.Boolean(
        string="Habilitar Reportes de Vacaciones",
        help="Habilitar reportes de vacaciones",
        default=True
    )
    
    # Configuración de integración
    integrate_with_accounting = fields.Boolean(
        string="Integrar con Contabilidad",
        help="Integrar nómina con módulo de contabilidad",
        default=False
    )
    
    auto_create_journal_entries = fields.Boolean(
        string="Crear Asientos Automáticamente",
        help="Crear asientos contables automáticamente al procesar nóminas",
        default=False
    )
    
    # Configuración de notificaciones
    enable_email_notifications = fields.Boolean(
        string="Habilitar Notificaciones por Email",
        help="Enviar notificaciones por email para eventos importantes",
        default=True
    )
    
    notify_loan_approval = fields.Boolean(
        string="Notificar Aprobación de Préstamos",
        help="Enviar notificación cuando se apruebe un préstamo",
        default=True
    )
    
    notify_vacation_payout = fields.Boolean(
        string="Notificar Pagos de Vacaciones",
        help="Enviar notificación cuando se procese un pago de vacaciones",
        default=True
    )
    
    # Configuración de auditoría
    enable_audit_log = fields.Boolean(
        string="Habilitar Log de Auditoría",
        help="Registrar todas las acciones importantes en log de auditoría",
        default=True
    )
    
    audit_retention_days = fields.Integer(
        string="Días de Retención de Auditoría",
        help="Número de días para retener logs de auditoría",
        default=365
    )
    
    @api.onchange('module_hr_loan_management')
    def _onchange_loan_management(self):
        """Manejar cambios en la instalación del módulo de préstamos"""
        if self.module_hr_loan_management:
            # Habilitar configuraciones relacionadas
            self.enable_loan_reports = True
            self.notify_loan_approval = True
    
    @api.onchange('module_hr_vacation_payout')
    def _onchange_vacation_payout(self):
        """Manejar cambios en la instalación del módulo de vacaciones"""
        if self.module_hr_vacation_payout:
            # Habilitar configuraciones relacionadas
            self.enable_vacation_reports = True
            self.notify_vacation_payout = True
    
    @api.onchange('module_hr_security')
    def _onchange_hr_security(self):
        """Manejar cambios en la instalación del módulo de seguridad"""
        if self.module_hr_security:
            # Habilitar configuraciones relacionadas
            self.enable_audit_log = True
    
    @api.onchange('integrate_with_accounting')
    def _onchange_accounting_integration(self):
        """Manejar cambios en la integración con contabilidad"""
        if not self.integrate_with_accounting:
            self.auto_create_journal_entries = False
    
    def set_values(self):
        """Guardar valores de configuración"""
        super().set_values()
        
        # Guardar configuraciones en parámetros del sistema
        config_params = self.env['ir.config_parameter'].sudo()
        
        config_params.set_param('payroll_management.validate_bank_accounts', str(self.validate_bank_accounts))
        config_params.set_param('payroll_management.validate_identification', str(self.validate_identification))
        config_params.set_param('payroll_management.max_loan_installments', str(self.max_loan_installments))
        config_params.set_param('payroll_management.max_txt_payslips', str(self.max_txt_payslips))
        config_params.set_param('payroll_management.enable_payroll_reports', str(self.enable_payroll_reports))
        config_params.set_param('payroll_management.enable_loan_reports', str(self.enable_loan_reports))
        config_params.set_param('payroll_management.enable_vacation_reports', str(self.enable_vacation_reports))
        config_params.set_param('payroll_management.integrate_with_accounting', str(self.integrate_with_accounting))
        config_params.set_param('payroll_management.auto_create_journal_entries', str(self.auto_create_journal_entries))
        config_params.set_param('payroll_management.enable_email_notifications', str(self.enable_email_notifications))
        config_params.set_param('payroll_management.notify_loan_approval', str(self.notify_loan_approval))
        config_params.set_param('payroll_management.notify_vacation_payout', str(self.notify_vacation_payout))
        config_params.set_param('payroll_management.enable_audit_log', str(self.enable_audit_log))
        config_params.set_param('payroll_management.audit_retention_days', str(self.audit_retention_days))
        
        if self.payroll_currency_id:
            config_params.set_param('payroll_management.payroll_currency_id', str(self.payroll_currency_id.id))
        
        if self.payroll_company_id:
            config_params.set_param('payroll_management.payroll_company_id', str(self.payroll_company_id.id))
        
        _logger.info("Configuración de payroll_management guardada")
    
    @api.model
    def get_values(self):
        """Obtener valores de configuración"""
        res = super().get_values()
        
        config_params = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'validate_bank_accounts': config_params.get_param('payroll_management.validate_bank_accounts', 'True') == 'True',
            'validate_identification': config_params.get_param('payroll_management.validate_identification', 'True') == 'True',
            'max_loan_installments': int(config_params.get_param('payroll_management.max_loan_installments', '10')),
            'max_txt_payslips': int(config_params.get_param('payroll_management.max_txt_payslips', '1000')),
            'enable_payroll_reports': config_params.get_param('payroll_management.enable_payroll_reports', 'True') == 'True',
            'enable_loan_reports': config_params.get_param('payroll_management.enable_loan_reports', 'True') == 'True',
            'enable_vacation_reports': config_params.get_param('payroll_management.enable_vacation_reports', 'True') == 'True',
            'integrate_with_accounting': config_params.get_param('payroll_management.integrate_with_accounting', 'False') == 'True',
            'auto_create_journal_entries': config_params.get_param('payroll_management.auto_create_journal_entries', 'False') == 'True',
            'enable_email_notifications': config_params.get_param('payroll_management.enable_email_notifications', 'True') == 'True',
            'notify_loan_approval': config_params.get_param('payroll_management.notify_loan_approval', 'True') == 'True',
            'notify_vacation_payout': config_params.get_param('payroll_management.notify_vacation_payout', 'True') == 'True',
            'enable_audit_log': config_params.get_param('payroll_management.enable_audit_log', 'True') == 'True',
            'audit_retention_days': int(config_params.get_param('payroll_management.audit_retention_days', '365')),
        })
        
        # Obtener moneda y compañía
        currency_id = config_params.get_param('payroll_management.payroll_currency_id')
        if currency_id:
            res['payroll_currency_id'] = int(currency_id)
        else:
            res['payroll_currency_id'] = self.env.company.currency_id.id
        
        company_id = config_params.get_param('payroll_management.payroll_company_id')
        if company_id:
            res['payroll_company_id'] = int(company_id)
        else:
            res['payroll_company_id'] = self.env.company.id
        
        return res 