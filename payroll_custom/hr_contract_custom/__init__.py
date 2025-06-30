# -*- coding: utf-8 -*-

from . import models

def post_init_hook(cr, registry=None):
    """Hook post-instalación para configuraciones iniciales"""
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Configurar parámetros por defecto si no existen
        config_params = env['ir.config_parameter'].sudo()
        
        # Parámetro para validación de fechas en líneas de salario
        if not config_params.get_param('hr_contract_custom.validate_dates'):
            config_params.set_param('hr_contract_custom.validate_dates', 'True')
        
        # Parámetro para conversión automática de monedas
        if not config_params.get_param('hr_contract_custom.auto_currency_conversion'):
            config_params.set_param('hr_contract_custom.auto_currency_conversion', 'True')
        
        _logger.info("Configuración post-instalación de hr_contract_custom completada")
        
    except Exception as e:
        _logger.error(f"Error en post_init_hook de hr_contract_custom: {str(e)}") 