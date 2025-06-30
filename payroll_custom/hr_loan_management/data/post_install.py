from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def _add_rule_to_structures(cr, registry):
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        rule = env.ref('hr_loan_management.hr_salary_rule_prestamo', False)
        if not rule:
            _logger.warning("No se encontró la regla salarial para préstamos")
            return
            
        structures = env['hr.payroll.structure'].search([])
        if not structures:
            _logger.warning("No se encontraron estructuras salariales")
            return
            
        for structure in structures:
            try:
                if rule.id not in structure.rule_ids.ids:
                    structure.write({'rule_ids': [(4, rule.id)]})
                    _logger.info(f"Regla de préstamo añadida a la estructura: {structure.name}")
            except Exception as e:
                _logger.error(f"Error al añadir la regla a la estructura {structure.name}: {str(e)}")
                
        env.cr.commit()
        _logger.info("Proceso de añadir regla de préstamo a estructuras completado")
    except Exception as e:
        _logger.error(f"Error en _add_rule_to_structures: {str(e)}")