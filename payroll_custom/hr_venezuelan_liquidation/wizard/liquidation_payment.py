# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrLiquidationPaymentWizard(models.TransientModel):
    _name = 'hr.liquidation.payment.wizard'
    _description = 'Asistente de Pago de Liquidación'

    liquidation_id     = fields.Many2one('hr.liquidation', string='Liquidación', required=True)
    payment_date       = fields.Date(string='Fecha de Pago', required=True, default=fields.Date.context_today)
    payment_reference  = fields.Char(string='Referencia de Pago', required=True)
    payment_method     = fields.Selection([('transfer','Transferencia Bancaria'),('check','Cheque'),('cash','Efectivo')], string='Método de Pago', required=True)
    notes              = fields.Text(string='Notas')

    @api.constrains('payment_date')
    def _check_payment_date(self):
        for rec in self:
            if rec.payment_date < rec.liquidation_id.date_end:
                raise ValidationError(_('La fecha de pago no puede ser anterior a la fecha de terminación.'))

    def action_register_payment(self):
        self.ensure_one()
        self.liquidation_id.write({
            'payment_date': self.payment_date,
            'payment_reference': self.payment_reference,
            'state': 'done'
        })
        msg = _('Pago registrado:\nFecha: %s\nReferencia: %s\nMétodo: %s\nNotas: %s') % (
            self.payment_date,
            self.payment_reference,
            dict(self._fields['payment_method'].selection).get(self.payment_method),
            self.notes or ''
        )
        self.liquidation_id.message_post(body=msg)
        return {'type':'ir.actions.act_window_close'}
