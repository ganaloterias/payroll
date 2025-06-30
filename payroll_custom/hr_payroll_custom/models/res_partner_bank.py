from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    x_type = fields.Selection([('national', 'V'),('foreign', 'E'),('juridical', 'J'),('passport', 'P'),('government', 'G'),], string="Tipo de Identificación", help="Tipo de Identificación: V: Venezolano, E: Extranjero, J: Jurídico, P: Pasaporte, G: Gobierno")
    x_identification_id = fields.Char(string="Cédula", help="Número de Cédula de Identidad")
    x_payment_type = fields.Selection([('Transferencia Swift', '00'),('Abono de Cuenta BdV', '01'),('Cheque de Gerencia', '02'),], string="Tipo de Pago", help="Tipo de Pago: 1: Transferencia Swift, 2: Abono de Cuenta BdV, 3: Cheque de Gerencia")
    x_credit_reference = fields.Char(string="N° de Referencia de Crédito", help="Número de Referencia de Crédito")
    x_account_type = fields.Selection([('corriente', '00'),('ahorro', '01'),], string="Tipo de Cuenta", help="Tipor de cuenta Bancaria 00 = Corriente, 01 = Ahorro")
    x_check_duration = fields.Integer(string="Duración del Cheque (Días)", help="Duración del Cheque en Días")
    x_beneficiary_email = fields.Char(string="Email del Beneficiario", help="Email del Beneficiario no es obligatorio")
    allow_out_payment = fields.Boolean(string="Permitir Pagos Salientes",help="Si está marcado, permite realizar pagos desde esta cuenta bancaria.")
