from odoo import fields, models

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
