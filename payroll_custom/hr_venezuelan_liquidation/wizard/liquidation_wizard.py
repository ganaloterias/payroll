from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LiquidationWizard(models.TransientModel):
    _name = 'hr.liquidation.wizard'
    _description = 'Asistente de Liquidación'

    employee_id      = fields.Many2one('hr.employee', required=True)
    date_end         = fields.Date(required=True, default=fields.Date.context_today)
    reason           = fields.Selection([('resignation','Renuncia'),('dismissal','Despido')], string='Tipo de Liquidación', required=True)
    notes            = fields.Text()

    def action_create_liquidation(self):
        self.ensure_one()
        contract = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id),('state','=','open')], limit=1)
        if not contract:
            raise ValidationError(_('El empleado no tiene contrato activo.'))
        liquidation = self.env['hr.liquidation'].create({
            'employee_id': self.employee_id.id,
            'liquidation_type': self.reason,
            'date_start': contract.date_start,
            'date_end': self.date_end,
            'currency_id': self.env.company.currency_id.id,
            'last_wage': contract.wage
        })
        body = _('Liquidación creada por %s') % self.env.user.name
        liquidation.message_post(body=body)
        return {
            'type':'ir.actions.act_window',
            'res_model':'hr.liquidation',
            'res_id':liquidation.id,
            'view_mode':'form'
        }
