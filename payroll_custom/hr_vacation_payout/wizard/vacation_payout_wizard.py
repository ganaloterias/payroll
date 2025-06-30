# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class HrVacationPayoutWizard(models.TransientModel):
    _name = 'hr.vacation.payout.wizard'
    _description = 'Asistente de Pago de Vacaciones'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    date = fields.Date(string='Fecha de Pago', required=True, default=fields.Date.context_today)
    vacation_days = fields.Float(string='Días de Vacaciones', required=True, default=15.0)
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                  default=lambda self: self.env.company.currency_id.id, required=True)
    last_wage = fields.Monetary(string='Último Salario', currency_field='currency_id', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato', readonly=True)
    work_years = fields.Float(string='Años de Servicio', readonly=True)
    
    @api.onchange('employee_id')
    def _onchange_employee(self):
        """Maneja los cambios cuando se selecciona un empleado"""
        if not self.employee_id:
            self.contract_id = False
            self.last_wage = 0.0
            self.work_years = 0.0
            return
            
        # Buscar contrato activo
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open')
        ], limit=1)
        
        if not contract:
            self.contract_id = False
            self.last_wage = 0.0
            self.work_years = 0.0
            return {
                'warning': {
                    'title': _('Advertencia'),
                    'message': _("El empleado no tiene un contrato activo.")
                }
            }
            
        self.contract_id = contract.id
        
        # Calcular años de servicio
        if self.date and contract.date_start:
            delta = self.date - contract.date_start
            self.work_years = delta.days / 365.0
            
        # Buscar última nómina
        payslip = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'done')
        ], order='date_to desc', limit=1)
        
        if not payslip:
            self.last_wage = 0.0
            return {
                'warning': {
                    'title': _('Advertencia'),
                    'message': _("El empleado no tiene nóminas procesadas. Se debe ingresar el salario manualmente.")
                }
            }
            
        # Obtener salario neto
        net_line = next((line for line in payslip.line_ids if line.code == 'NET'), None)
        if net_line:
            self.last_wage = net_line.total
        else:
            self.last_wage = 0.0
            return {
                'warning': {
                    'title': _('Advertencia'),
                    'message': _("No se pudo determinar el salario del empleado. Se debe ingresar manualmente.")
                }
            }
            
    def action_create_payout(self):
        """Crea un nuevo registro de pago de vacaciones"""
        self.ensure_one()
        
        if not self.employee_id:
            raise UserError(_("Debe seleccionar un empleado."))
            
        if not self.last_wage or self.last_wage <= 0:
            raise UserError(_("El salario debe ser mayor que cero."))
            
        if not self.vacation_days or self.vacation_days <= 0:
            raise UserError(_("Los días de vacaciones deben ser mayores que cero."))
            
        # Crear registro de pago de vacaciones
        payout_vals = {
            'employee_id': self.employee_id.id,
            'date': self.date,
            'vacation_days': self.vacation_days,
            'last_wage': self.last_wage,
            'currency_id': self.currency_id.id,
        }
        
        try:
            payout = self.env['hr.vacation.payout'].create(payout_vals)
            _logger.info(f"Pago de vacaciones creado con ID: {payout.id}")
            
            # Retornar acción para mostrar el registro creado
            return {
                'name': _('Pago de Vacaciones'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.vacation.payout',
                'res_id': payout.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error al crear pago de vacaciones: {str(e)}")
            raise UserError(_("Error al crear el pago de vacaciones: %s") % str(e)) 