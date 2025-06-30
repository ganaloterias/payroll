# -*- coding: utf-8 -*-

from . import models

def post_init_hook(cr, registry=None):
    """Hook post-instalación para configuraciones iniciales del sistema de nómina"""
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Configurar parámetros por defecto del sistema de nómina
        config_params = env['ir.config_parameter'].sudo()
        
        # Configuraciones de validación
        if not config_params.get_param('payroll_management.validate_bank_accounts'):
            config_params.set_param('payroll_management.validate_bank_accounts', 'True')
        
        if not config_params.get_param('payroll_management.validate_identification'):
            config_params.set_param('payroll_management.validate_identification', 'True')
        
        # Configuraciones de límites
        if not config_params.get_param('payroll_management.max_loan_installments'):
            config_params.set_param('payroll_management.max_loan_installments', '10')
        
        if not config_params.get_param('payroll_management.max_txt_payslips'):
            config_params.set_param('payroll_management.max_txt_payslips', '1000')
        
        # Configuraciones de reportes
        if not config_params.get_param('payroll_management.enable_payroll_reports'):
            config_params.set_param('payroll_management.enable_payroll_reports', 'True')
        
        if not config_params.get_param('payroll_management.enable_loan_reports'):
            config_params.set_param('payroll_management.enable_loan_reports', 'True')
        
        if not config_params.get_param('payroll_management.enable_vacation_reports'):
            config_params.set_param('payroll_management.enable_vacation_reports', 'True')
        
        # Configuraciones de integración
        if not config_params.get_param('payroll_management.integrate_with_accounting'):
            config_params.set_param('payroll_management.integrate_with_accounting', 'False')
        
        if not config_params.get_param('payroll_management.auto_create_journal_entries'):
            config_params.set_param('payroll_management.auto_create_journal_entries', 'False')
        
        # Configuraciones de notificaciones
        if not config_params.get_param('payroll_management.enable_email_notifications'):
            config_params.set_param('payroll_management.enable_email_notifications', 'True')
        
        if not config_params.get_param('payroll_management.notify_loan_approval'):
            config_params.set_param('payroll_management.notify_loan_approval', 'True')
        
        if not config_params.get_param('payroll_management.notify_vacation_payout'):
            config_params.set_param('payroll_management.notify_vacation_payout', 'True')
        
        # Configuraciones de auditoría
        if not config_params.get_param('payroll_management.enable_audit_log'):
            config_params.set_param('payroll_management.enable_audit_log', 'True')
        
        if not config_params.get_param('payroll_management.audit_retention_days'):
            config_params.set_param('payroll_management.audit_retention_days', '365')
        
        # Configurar moneda y compañía por defecto
        if not config_params.get_param('payroll_management.payroll_currency_id'):
            config_params.set_param('payroll_management.payroll_currency_id', str(env.company.currency_id.id))
        
        if not config_params.get_param('payroll_management.payroll_company_id'):
            config_params.set_param('payroll_management.payroll_company_id', str(env.company.id))
        
        _logger.info("Configuración post-instalación de payroll_management completada")
        
    except Exception as e:
        _logger.error(f"Error en post_init_hook de payroll_management: {str(e)}")
