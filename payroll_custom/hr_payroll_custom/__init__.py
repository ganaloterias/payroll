# -*- coding: utf-8 -*-

from . import models
from . import wizard

def post_init_hook(cr, registry=None):
    """Hook post-instalación para configuraciones iniciales"""
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Configurar parámetros por defecto si no existen
        config_params = env['ir.config_parameter'].sudo()
        
        # Parámetro para validación de límites en generación de TXT
        if not config_params.get_param('hr_payroll_custom.txt_max_payslips'):
            config_params.set_param('hr_payroll_custom.txt_max_payslips', '1000')
        
        # Parámetro para validación de cuentas bancarias
        if not config_params.get_param('hr_payroll_custom.validate_bank_accounts'):
            config_params.set_param('hr_payroll_custom.validate_bank_accounts', 'True')
        
        _logger.info("Configuración post-instalación de hr_payroll_custom completada")
        
    except Exception as e:
        _logger.error(f"Error en post_init_hook de hr_payroll_custom: {str(e)}")
