from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Partner(models.Model):
    _inherit = 'res.partner'

    ordenante_account_number = fields.Char(string="Número de Cuenta Ordenante", help="Número de cuenta del ordenante")
    type_account = fields.Selection([('corriente', '00'), ('ahorro', '01')], string="Tipo de Cuenta", help="00 = Corriente, 01 = Ahorro.")
    ref_lot = fields.Char(string="Referencia de Lote", help="Número de referencia de lote")
    number_negotiation = fields.Char(string="Número de Negociación", help="Número de negociación")

    @api.constrains('ordenante_account_number')
    def _check_account_number(self):
        for record in self:
            if record.ordenante_account_number and not record.ordenante_account_number.isdigit():
                raise ValidationError("El número de cuenta ordenante solo puede contener dígitos.")
