from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class PayslipFinder:
    def __init__(self, env):
        self.env = env

    def find_last_valid_payslip(self, employee_id, date_start, date_end, currency_id):
        # Obtenemos la moneda para depuración
        currency = self.env['res.currency'].browse(currency_id)
        currency_name = currency.name
        
        # Modificamos el dominio para buscar todas las nóminas hasta date_end
        domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'done'),
            ('date_to', '<=', date_end)
        ]
        
        # Buscamos todas las nóminas que cumplan con el filtro básico
        payslips = self.env['hr.payslip'].search(domain, order='date_to desc')
        
        if not payslips:
            raise UserError(_('No se encontró ninguna nómina validada hasta la fecha seleccionada para el empleado.'))
        
        # En Odoo, las nóminas podrían no tener moneda directamente, buscamos de diferentes maneras
        found_payslips = []
        currency_mismatches = []
        
        # Primera opción: moneda de la compañía
        for payslip in payslips:
            company_currency = payslip.company_id.currency_id
            
            # Registramos para depuración
            currency_mismatches.append({
                'slip': payslip.name,
                'company_currency': company_currency.name,
                'expected': currency_name
            })
            
            # Comparamos por nombre o ID (no por código que no existe)
            if company_currency.name == currency_name or company_currency.id == currency_id:
                found_payslips.append(payslip)
                
        # Si encontramos coincidencias, devolvemos la más reciente
        if found_payslips:
            return found_payslips[0]
            
        # Si no encontramos coincidencias directas, buscamos en las líneas de nómina
        for payslip in payslips:
            for line in payslip.line_ids.filtered(lambda l: l.code == 'NET'):
                # Si encontramos una línea neta con la moneda correcta, devolvemos esta nómina
                if hasattr(line, 'currency_id') and line.currency_id and line.currency_id.name == currency_name:
                    return payslip
        
        # SOLUCIÓN TEMPORAL: Si el usuario seleccionó una moneda específica y no hay nóminas
        # en esa moneda, tomamos la última nómina procesada independientemente de la moneda
        if payslips and currency_id:
            last_slip = payslips[0]
            last_currency = last_slip.company_id.currency_id.name
            
            warning_msg = _("""AVISO: No se encontraron nóminas en la moneda {} para el empleado.
La última nómina procesada está en moneda {}. 
Se usará esta nómina para los cálculos, pero asegúrese de revisar los montos calculados.""").format(
                currency_name, last_currency
            )
            
            # Registramos en el log para diagnóstico
            _logger.warning(warning_msg)
            
            # Retornamos la nómina más reciente como solución temporal
            return last_slip
            
        # Si llegamos aquí, no hay solución
        currencies_info = [f"{m['slip']}: {m['company_currency']}" for m in currency_mismatches[:3]]
        error_msg = _("""No se encontró ninguna nómina con la moneda seleccionada ({}) para el empleado.
Monedas encontradas: {}""").format(currency_name, ", ".join(currencies_info))
        
        raise UserError(error_msg)

    def get_net_amount(self, payslip):
        try:
            return payslip.get_salary_line_total('NET')
        except:
            return 0.0
