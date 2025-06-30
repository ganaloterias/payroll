# -*- coding: utf-8 -*-

def post_init_hook(cr, registry=None):
    """Hook post-instalación para configuraciones de seguridad"""
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Configurar parámetros de seguridad por defecto
        config_params = env['ir.config_parameter'].sudo()
        
        # Parámetro para auditoría de acceso
        if not config_params.get_param('hr_security.audit_access'):
            config_params.set_param('hr_security.audit_access', 'True')
        
        # Parámetro para validación de permisos
        if not config_params.get_param('hr_security.validate_permissions'):
            config_params.set_param('hr_security.validate_permissions', 'True')
        
        # Parámetro para tiempo de sesión
        if not config_params.get_param('hr_security.session_timeout'):
            config_params.set_param('hr_security.session_timeout', '3600')
        
        _logger.info("Configuración post-instalación de hr_security completada")
        
    except Exception as e:
        _logger.error(f"Error en post_init_hook de hr_security: {str(e)}")
