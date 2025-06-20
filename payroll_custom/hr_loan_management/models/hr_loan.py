from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class HrLoan(models.Model):
    _name = 'hr.loan'
    _description = 'Employee Loan'

    name = fields.Char(string="Referencia", required=True, default='Nuevo Préstamo')
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary(string="Monto del préstamo", required=True)
    installment_count = fields.Integer(string="Número de cuotas", default=1)
    installment_amount = fields.Monetary(string="Monto por cuota", compute='_compute_installment_amount', store=True)
    start_date = fields.Date(string="Fecha de inicio", required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('running', 'En curso'),
        ('done', 'Completado'),
    ], default='draft', string="Estado", tracking=True)
    installment_ids = fields.One2many('hr.loan.installment', 'loan_id', string="Cuotas")

    all_installments_paid = fields.Boolean(
        string="¿Todas las cuotas pagadas?",
        compute="_compute_all_installments_paid",
        store=True
    )
    
    remaining_amount = fields.Monetary(string="Saldo Pendiente",compute="_compute_remaining_amount",store=True,)

    @api.depends('installment_ids.paid', 'installment_ids.amount')
    def _compute_remaining_amount(self):
        for loan in self:
            unpaid_installments = loan.installment_ids.filtered(lambda i: not i.paid)
            loan.remaining_amount = sum(unpaid_installments.mapped('amount'))


    @api.depends('installment_ids.paid')
    def _compute_all_installments_paid(self):
        for loan in self:
            loan.all_installments_paid = all(installment.paid for installment in loan.installment_ids)

    @api.depends('amount', 'installment_count')
    def _compute_installment_amount(self):
        for loan in self:
            if loan.installment_count > 0:
                loan.installment_amount = loan.amount / loan.installment_count

    def action_approve(self):
        for loan in self:
            if loan.state != 'draft':
                raise ValidationError("Solo puedes aprobar préstamos en estado Borrador.")
            if loan.installment_count > 10:
                raise ValidationError("El número máximo de cuotas es 10.")
            if loan.installment_ids:
                raise ValidationError("Ya se han generado las cuotas para este préstamo.")
            loan.name = self.env['ir.sequence'].next_by_code('hr.loan') or 'New'
            loan._generate_installments()
            loan.state = 'approved'

    def action_start(self):
        for loan in self:
            if loan.state != 'approved':
                raise ValidationError("Solo puedes iniciar préstamos que estén Aprobados.")
            loan.state = 'running'

    def action_done(self):
        for loan in self:
            if loan.state != 'running':
                raise ValidationError("Solo puedes completar préstamos En Curso.")
            if not loan.all_installments_paid:
                raise ValidationError("No puedes finalizar el préstamo hasta que todas las cuotas estén pagadas.")
            loan.state = 'done'

    def _generate_installments(self):
        for loan in self:
            if loan.installment_ids:
                raise ValidationError("Este préstamo ya tiene cuotas generadas.")

            installments = []
            current_date = loan.start_date
            while len(installments) < loan.installment_count:
                if current_date.day < 15:
                    due_date = current_date.replace(day=15)
                else:
                    due_date = current_date.replace(day=30 if current_date.month != 2 else 28)
                if due_date <= current_date:
                    due_date += timedelta(days=15)
                installments.append((0, 0, {
                    'date_due': due_date,
                    'amount': loan.installment_amount,
                }))
                current_date = due_date + timedelta(days=1)
            loan.installment_ids = installments
