from odoo import fields, models

class HrLoanInstallment(models.Model):
    _name = 'hr.loan.installment'
    _description = 'Loan Installment'

    loan_id = fields.Many2one('hr.loan', string="Loan", required=True, ondelete='cascade')
    date_due = fields.Date(string="Due Date", required=True)
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(related='loan_id.currency_id', store=True)
    paid = fields.Boolean(string="Paid", default=False)
    payslip_id = fields.Many2one('hr.payslip', string="Nómina aplicada", ondelete='set null', readonly=True)
    