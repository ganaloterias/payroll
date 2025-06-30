# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Obtener inputs base y añadir vacaciones"""
        # Llamamos al método original para obtener los inputs base
        res = super().get_inputs(contracts, date_from, date_to)
        
        # Añadir inputs de vacaciones
        res.extend(self._get_vacation_inputs(contracts, date_from, date_to))
        
        return res

    def _get_vacation_inputs(self, contracts, date_from, date_to):
        """Obtener inputs de vacaciones para el período"""
        inputs = []
        
        for contract in contracts:
            employee = contract.employee_id
            if not employee:
                continue
                
            # Buscar pagos de vacaciones validados para el período
            vacation_payouts = self.env['hr.vacation.payout'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validated'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', contract.company_id.id),
            ])
            
            for payout in vacation_payouts:
                # Verificar que la moneda coincida
                if payout.currency_id.id != contract.company_id.currency_id.id:
                    _logger.warning(
                        "Moneda del pago de vacaciones %s no coincide con la moneda de la empresa %s",
                        payout.name, contract.company_id.name
                    )
                    continue
                
                # Añadir input de vacaciones
                inputs.append({
                    'name': _('Pago de Vacaciones - %s') % payout.name,
                    'code': 'VACATION_PAY',
                    'contract_id': contract.id,
                    'amount': payout.total_amount,
                    'vacation_payout_id': payout.id,
                })
        
        return inputs

    @api.onchange('employee_id', 'date_from', 'date_to', 'struct_id')
    def onchange_employee(self):
        """Sobrescribir onchange para añadir vacaciones"""
        # Primero ejecutamos el método original
        result = super().onchange_employee()
        
        # Si no tenemos empleado o fechas, no continuamos
        if not self.employee_id or not self.date_from or not self.date_to:
            return result
        
        # Añadir vacaciones solo si hay contrato
        if self.contract_id:
            self._add_vacation_inputs_onchange()
        
        return result
    
    def _add_vacation_inputs_onchange(self):
        """Añadir inputs de vacaciones durante onchange"""
        self.ensure_one()
        
        try:
            # Limpiar inputs de vacaciones existentes
            existing_inputs = self.input_line_ids.filtered(
                lambda line: line.code == 'VACATION_PAY'
            )
            if existing_inputs:
                self.input_line_ids = [(2, input_id) for input_id in existing_inputs.ids]
            
            # Obtener nuevos inputs de vacaciones
            vacation_inputs = self._get_vacation_inputs([self.contract_id], self.date_from, self.date_to)
            
            # Añadir nuevos inputs
            for input_data in vacation_inputs:
                self.input_line_ids = [(0, 0, input_data)]
                
        except Exception as e:
            _logger.error("Error al añadir inputs de vacaciones: %s", str(e))
            # No mostrar error al usuario durante onchange

    def compute_sheet(self):
        """Sobrescribir compute_sheet para asegurar inputs de vacaciones"""
        # Asegurarse de que las entradas de vacaciones están presentes antes de calcular
        for payslip in self:
            if payslip.contract_id:
                payslip._add_vacation_inputs_onchange()
        
        return super().compute_sheet()

    def action_payslip_done(self):
        """Sobrescribir action_payslip_done para marcar pagos como procesados"""
        # Llamar al método original primero
        res = super().action_payslip_done()

        # Procesar pagos de vacaciones
        for payslip in self:
            payslip._process_vacation_payments()

        return res

    def _process_vacation_payments(self):
        """Procesar pagos de vacaciones en la nómina"""
        self.ensure_one()
        
        try:
            # Buscar inputs de vacaciones con monto positivo
            vacation_inputs = self.input_line_ids.filtered(
                lambda line: line.code == 'VACATION_PAY' and line.amount > 0
            )
            
            for input_line in vacation_inputs:
                payout_id = input_line.vacation_payout_id.id if input_line.vacation_payout_id else False
                
                if payout_id:
                    # Actualizar pago específico
                    payout = self.env['hr.vacation.payout'].browse(payout_id)
                    if payout.exists() and payout.state == 'validated':
                        payout.write({
                            'state': 'done',
                        })
                        
                        # Mensaje de confirmación
                        self.message_post(
                            body=_("Pago de vacaciones %s procesado en nómina.") % payout.name
                        )
                        
        except Exception as e:
            _logger.error("Error al procesar pagos de vacaciones: %s", str(e))
            # No fallar la nómina por este error

    def action_payslip_cancel(self):
        """Sobrescribir cancel para revertir pagos de vacaciones"""
        # Revertir pagos de vacaciones antes de cancelar
        for payslip in self:
            payslip._revert_vacation_payments()
        
        return super().action_payslip_cancel()

    def _revert_vacation_payments(self):
        """Revertir pagos de vacaciones al cancelar nómina"""
        self.ensure_one()
        
        try:
            # Buscar pagos procesados por esta nómina
            vacation_inputs = self.input_line_ids.filtered(
                lambda line: line.code == 'VACATION_PAY' and line.amount > 0
            )
            
            for input_line in vacation_inputs:
                if input_line.vacation_payout_id and input_line.vacation_payout_id.state == 'done':
                    input_line.vacation_payout_id.write({'state': 'validated'})
                    
            if vacation_inputs:
                self.message_post(
                    body=_("Se han revertido %s pagos de vacaciones al cancelar la nómina.") % len(vacation_inputs)
                )
                
        except Exception as e:
            _logger.error("Error al revertir pagos de vacaciones: %s", str(e))
            # No fallar la cancelación por este error


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    
    vacation_payout_id = fields.Many2one(
        'hr.vacation.payout', 
        string='Pago de vacaciones',
        help='Pago de vacaciones asociado a esta entrada de nómina',
        ondelete='set null'
    )
    
    @api.constrains('amount', 'vacation_payout_id')
    def _check_vacation_amount(self):
        """Validar que el monto coincida con el pago"""
        for record in self:
            if record.vacation_payout_id and record.amount != record.vacation_payout_id.total_amount:
                raise UserError(_(
                    "El monto del input (%s) no coincide con el monto del pago de vacaciones (%s)."
                ) % (record.amount, record.vacation_payout_id.total_amount)) 