from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def _setup_vacation_leave_type(cr, registry):
    """
    Configura automáticamente el tipo de ausencia para vacaciones.
    Este método se ejecuta después de que el módulo se ha instalado.
    """
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Buscar si ya existe un tipo de ausencia para vacaciones
        leave_type = env['hr.leave.type'].search([
            ('code', '=', 'VACATION')
        ], limit=1)
        
        if not leave_type:
            # Crear tipo de ausencia para vacaciones
            leave_type = env['hr.leave.type'].create({
                'name': 'Vacaciones',
                'code': 'VACATION',
                'allocation_type': 'no',
                'validation_type': 'hr',
                'requires_allocation': 'no',
                'employee_requests': 'yes',
                'color_name': 'success',
            })
            _logger.info("Tipo de ausencia para vacaciones creado automáticamente")
        else:
            # Asegurar que tenga el código correcto
            if not leave_type.code:
                leave_type.write({'code': 'VACATION'})
                _logger.info("Código VACATION asignado al tipo de ausencia existente")
        
        # Buscar tipos de ausencia que parezcan vacaciones pero no tengan código
        vacation_like_types = env['hr.leave.type'].search([
            '|', ('name', 'ilike', 'vaca'), ('name', 'ilike', 'vacation'),
            ('code', '=', False)
        ])
        
        for lt in vacation_like_types:
            lt.write({'code': 'VACATION'})
            _logger.info(f"Código VACATION asignado a: {lt.name}")
            
        env.cr.commit()
        _logger.info("Configuración de tipos de ausencia para vacaciones completada")
        
    except Exception as e:
        _logger.error(f"Error en _setup_vacation_leave_type: {str(e)}")
        # No provocamos un fallo fatal, solo registramos el error

def _setup_vacation_salary_rules(cr, registry):
    """
    Configura las reglas salariales para vacaciones.
    """
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Crear categoría para vacaciones si no existe
        category = env['hr.salary.rule.category'].search([
            ('code', '=', 'VACATION_PAY')
        ], limit=1)
        
        if not category:
            category = env['hr.salary.rule.category'].create({
                'name': 'Pago de Vacaciones',
                'code': 'VACATION_PAY',
            })
            _logger.info("Categoría de regla salarial para vacaciones creada")
        
        # Crear regla salarial para vacaciones si no existe
        rule = env['hr.salary.rule'].search([
            ('code', '=', 'VACATION_PAY')
        ], limit=1)
        
        if not rule:
            rule = env['hr.salary.rule'].create({
                'name': 'Pago de Vacaciones',
                'code': 'VACATION_PAY',
                'sequence': 200,
                'category_id': category.id,
                'condition_select': 'python',
                'condition_python': 'result = inputs.VACATION_PAY and inputs.VACATION_PAY.amount > 0',
                'amount_select': 'code',
                'amount_python_compute': 'result = inputs.VACATION_PAY.amount',
                'appears_on_payslip': True,
            })
            _logger.info("Regla salarial para vacaciones creada")
        
        # Crear input para vacaciones si no existe
        input_rule = env['hr.rule.input'].search([
            ('code', '=', 'VACATION_PAY')
        ], limit=1)
        
        if not input_rule:
            env['hr.rule.input'].create({
                'name': 'Pago de Vacaciones',
                'code': 'VACATION_PAY',
                'input_id': rule.id,
            })
            _logger.info("Input de regla para vacaciones creado")
        
        env.cr.commit()
        _logger.info("Configuración de reglas salariales para vacaciones completada")
        
    except Exception as e:
        _logger.error(f"Error en _setup_vacation_salary_rules: {str(e)}")

def post_init_hook(cr, registry=None):
    """
    Hook que se ejecuta después de la instalación del módulo.
    Configura automáticamente los elementos necesarios.
    """
    _logger.info("Iniciando configuración post-instalación del módulo de vacaciones")
    
    _setup_vacation_leave_type(cr, registry)
    _setup_vacation_salary_rules(cr, registry)
    
    _logger.info("Configuración post-instalación del módulo de vacaciones completada") 