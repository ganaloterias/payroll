# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class HrLiquidationPaymentWizard(models.TransientModel):
    _name = 'hr.liquidation.payment.wizard'
    _description = 'Asistente de Pago de Liquidación'

    liquidation_id = fields.Many2one(
        'hr.liquidation', 
        string='Liquidación', 
        required=True,
        domain=[('state', '=', 'validated')],
        help='Liquidación a pagar'
    )
    payment_date = fields.Date(
        string='Fecha de Pago', 
        required=True, 
        default=fields.Date.context_today,
        help='Fecha en que se realiza el pago'
    )
    payment_reference = fields.Char(
        string='Referencia de Pago', 
        required=True,
        help='Número de referencia del pago (transferencia, cheque, etc.)'
    )
    payment_method = fields.Selection([
        ('transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('cash', 'Efectivo'),
        ('deposit', 'Depósito Bancario'),
        ('other', 'Otro')
    ], string='Método de Pago', required=True, default='transfer')
    notes = fields.Text(
        string='Notas',
        help='Observaciones adicionales sobre el pago'
    )
    
    # Campos computados para información
    employee_id = fields.Many2one(
        related='liquidation_id.employee_id',
        string='Empleado',
        readonly=True
    )
    total_amount = fields.Monetary(
        related='liquidation_id.total_liquidacion',
        string='Total a Pagar',
        readonly=True
    )
    currency_id = fields.Many2one(
        related='liquidation_id.currency_id',
        string='Moneda',
        readonly=True
    )

    @api.onchange('liquidation_id')
    def _onchange_liquidation(self):
        """Manejar cambios en la liquidación"""
        if not self.liquidation_id:
            return
        
        # Verificar que la liquidación esté validada
        if self.liquidation_id.state != 'validated':
            return {
                'warning': {
                    'title': _('Estado Incorrecto'),
                    'message': _('Solo puede registrar pagos para liquidaciones validadas.')
                }
            }
        
        # Verificar que no haya sido pagada ya
        if self.liquidation_id.state == 'done':
            return {
                'warning': {
                    'title': _('Ya Pagada'),
                    'message': _('Esta liquidación ya ha sido pagada.')
                }
            }

    @api.constrains('payment_date')
    def _check_payment_date(self):
        """Validar fecha de pago"""
        for record in self:
            if record.payment_date > date.today():
                raise ValidationError(_('La fecha de pago no puede ser futura.'))
            
            if record.liquidation_id and record.payment_date < record.liquidation_id.date_end:
                raise ValidationError(_('La fecha de pago no puede ser anterior a la fecha de terminación del contrato.'))

    @api.constrains('payment_reference')
    def _check_payment_reference(self):
        """Validar referencia de pago"""
        for record in self:
            if record.payment_reference and len(record.payment_reference.strip()) < 3:
                raise ValidationError(_('La referencia de pago debe tener al menos 3 caracteres.'))

    def action_register_payment(self):
        """Registrar el pago de la liquidación"""
        self.ensure_one()
        
        # Validaciones adicionales
        if not self.liquidation_id:
            raise UserError(_('Debe seleccionar una liquidación.'))
        
        if self.liquidation_id.state != 'validated':
            raise UserError(_('Solo puede registrar pagos para liquidaciones validadas.'))
        
        if not self.payment_reference:
            raise UserError(_('Debe especificar una referencia de pago.'))
        
        if not self.payment_date:
            raise UserError(_('Debe especificar la fecha de pago.'))
        
        try:
            # Actualizar liquidación
            self.liquidation_id.write({
                'state': 'done',
                'done_date': fields.Datetime.now(),
            })
            
            # Crear mensaje detallado
            payment_method_name = dict(self._fields['payment_method'].selection).get(self.payment_method, self.payment_method)
            
            message_body = _("""
                <strong>Pago Registrado</strong><br/>
                <ul>
                    <li><strong>Fecha de Pago:</strong> %s</li>
                    <li><strong>Referencia:</strong> %s</li>
                    <li><strong>Método:</strong> %s</li>
                    <li><strong>Monto:</strong> %s %s</li>
                </ul>
            """) % (
                self.payment_date,
                self.payment_reference,
                payment_method_name,
                self.total_amount,
                self.currency_id.symbol
            )
            
            if self.notes:
                message_body += _("<br/><strong>Notas:</strong><br/>%s") % self.notes
            
            # Publicar mensaje
            self.liquidation_id.message_post(
                body=message_body,
                subject=_('Pago Registrado')
            )
            
            _logger.info(f"Pago registrado para liquidación {self.liquidation_id.name}: {self.payment_reference}")
            
            # Retornar acción para mostrar la liquidación actualizada
            return {
                'name': _('Liquidación'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.liquidation',
                'res_id': self.liquidation_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"Error al registrar pago: {str(e)}")
            raise UserError(_('Error al registrar el pago: %s') % str(e))

    def action_view_liquidation(self):
        """Ver la liquidación"""
        self.ensure_one()
        return {
            'name': _('Liquidación'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.liquidation',
            'res_id': self.liquidation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
