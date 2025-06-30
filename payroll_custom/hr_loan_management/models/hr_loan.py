from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, date
import logging

_logger = logging.getLogger(__name__)

class HrLoan(models.Model):
    _name = 'hr.loan'
    _description = 'Employee Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'start_date desc, name desc'

    name = fields.Char(
        string="Referencia", 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: _('Nuevo Préstamo'),
        tracking=True
    )
    employee_id = fields.Many2one(
        'hr.employee', 
        string="Empleado", 
        required=True,
        tracking=True,
        ondelete='restrict'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True
    )
    amount = fields.Monetary(
        string="Monto del préstamo", 
        required=True,
        tracking=True,
        help="Monto total del préstamo a otorgar"
    )
    installment_count = fields.Integer(
        string="Número de cuotas", 
        default=1,
        tracking=True,
        help="Número máximo de cuotas permitidas: 10"
    )
    installment_amount = fields.Monetary(
        string="Monto por cuota", 
        compute='_compute_installment_amount', 
        store=True,
        help="Monto calculado por cada cuota"
    )
    start_date = fields.Date(
        string="Fecha de inicio", 
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('running', 'En curso'),
        ('done', 'Completado'),
        ('cancelled', 'Cancelado'),
    ], default='draft', string="Estado", tracking=True)
    
    installment_ids = fields.One2many(
        'hr.loan.installment', 
        'loan_id', 
        string="Cuotas",
        copy=False
    )

    all_installments_paid = fields.Boolean(
        string="¿Todas las cuotas pagadas?",
        compute="_compute_all_installments_paid",
        store=True
    )
    
    remaining_amount = fields.Monetary(
        string="Saldo Pendiente",
        compute="_compute_remaining_amount",
        store=True,
        help="Monto total pendiente por pagar"
    )
    
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        required=True, 
        default=lambda self: self.env.company
    )
    
    notes = fields.Text(string='Observaciones')

    @api.constrains('amount', 'installment_count')
    def _check_amount_and_installments(self):
        """Validar montos y número de cuotas"""
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("El monto del préstamo debe ser mayor que cero."))
            
            if record.installment_count <= 0:
                raise ValidationError(_("El número de cuotas debe ser mayor que cero."))
            
            if record.installment_count > 10:
                raise ValidationError(_("El número máximo de cuotas permitidas es 10."))

    @api.constrains('start_date')
    def _check_start_date(self):
        """Validar fecha de inicio"""
        for record in self:
            if record.start_date and record.start_date < date.today():
                raise ValidationError(_("La fecha de inicio no puede ser anterior a hoy."))

    @api.depends('installment_ids.paid', 'installment_ids.amount')
    def _compute_remaining_amount(self):
        """Calcular saldo pendiente"""
        for loan in self:
            unpaid_installments = loan.installment_ids.filtered(lambda i: not i.paid)
            loan.remaining_amount = sum(unpaid_installments.mapped('amount'))

    @api.depends('installment_ids.paid')
    def _compute_all_installments_paid(self):
        """Verificar si todas las cuotas están pagadas"""
        for loan in self:
            loan.all_installments_paid = all(installment.paid for installment in loan.installment_ids)

    @api.depends('amount', 'installment_count')
    def _compute_installment_amount(self):
        """Calcular monto por cuota"""
        for loan in self:
            if loan.installment_count > 0:
                loan.installment_amount = round(loan.amount / loan.installment_count, 2)
            else:
                loan.installment_amount = 0.0

    def action_approve(self):
        """Aprobar el préstamo y generar cuotas"""
        for loan in self:
            if loan.state != 'draft':
                raise UserError(_("Solo puedes aprobar préstamos en estado Borrador."))
            
            if loan.installment_count > 10:
                raise UserError(_("El número máximo de cuotas es 10."))
            
            if loan.installment_ids:
                raise UserError(_("Ya se han generado las cuotas para este préstamo."))
            
            loan.name = self.env['ir.sequence'].next_by_code('hr.loan') or _('Nuevo')
            
            loan._generate_installments()
            
            loan.state = 'approved'
            
            loan.message_post(
                body=_("Préstamo aprobado. Se han generado %s cuotas.") % loan.installment_count
            )

    def action_start(self):
        for loan in self:
            if loan.state != 'approved':
                raise UserError(_("Solo puedes iniciar préstamos que estén Aprobados."))
            
            loan.state = 'running'
            loan.message_post(body=_("Préstamo iniciado."))

    def action_done(self):
        for loan in self:
            if loan.state != 'running':
                raise UserError(_("Solo puedes completar préstamos En Curso."))
            
            if not loan.all_installments_paid:
                raise UserError(_("No puedes finalizar el préstamo hasta que todas las cuotas estén pagadas."))
            
            loan.state = 'done'
            loan.message_post(body=_("Préstamo completado."))

    def action_cancel(self):
        for loan in self:
            if loan.state not in ['draft', 'approved']:
                raise UserError(_("Solo puedes cancelar préstamos en estado Borrador o Aprobado."))
            
            loan.state = 'cancelled'
            loan.message_post(body=_("Préstamo cancelado."))

    def action_draft(self):
        for loan in self:
            if loan.state not in ['approved', 'cancelled']:
                raise UserError(_("Solo puedes volver a borrador desde estado Aprobado o Cancelado."))
            
            loan.state = 'draft'
            loan.message_post(body=_("Préstamo vuelto a borrador."))

    def _generate_installments(self):
        for loan in self:
            if loan.installment_ids:
                raise ValidationError(_("Este préstamo ya tiene cuotas generadas."))

            installments = []
            current_date = loan.start_date
            
            for i in range(loan.installment_count):
                due_date = self._calculate_due_date(current_date, i)
                
                if i == loan.installment_count - 1:
                    previous_amount = sum(inst[2]['amount'] for inst in installments) if installments else 0
                    installment_amount = loan.amount - previous_amount
                else:
                    installment_amount = loan.installment_amount
                
                installments.append((0, 0, {
                    'date_due': due_date,
                    'amount': round(installment_amount, 2),
                    'sequence': i + 1,
                }))
                
                current_date = due_date + timedelta(days=1)
            
            loan.installment_ids = installments

    def _calculate_due_date(self, start_date, installment_number):
        """Calcular fecha de vencimiento para una cuota específica"""
        if start_date.day < 15:
            due_date = start_date.replace(day=15)
        else:
            if start_date.month == 12:
                due_date = start_date.replace(year=start_date.year + 1, month=1, day=15)
            else:
                due_date = start_date.replace(month=start_date.month + 1, day=15)
        
        for _ in range(installment_number):
            if due_date.month == 12:
                due_date = due_date.replace(year=due_date.year + 1, month=1)
            else:
                due_date = due_date.replace(month=due_date.month + 1)
        
        return due_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id'):
                active_loans = self.search([
                    ('employee_id', '=', vals['employee_id']),
                    ('state', 'in', ['draft', 'approved', 'running'])
                ])
                if active_loans:
                    raise UserError(_("El empleado ya tiene un préstamo activo."))
        return super().create(vals_list)

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(_("No puedes eliminar un préstamo que no esté en borrador o cancelado."))
        return super().unlink()
