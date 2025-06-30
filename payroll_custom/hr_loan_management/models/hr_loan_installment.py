from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class HrLoanInstallment(models.Model):
    _name = 'hr.loan.installment'
    _description = 'Loan Installment'
    _order = 'sequence, date_due'

    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'digits' or super()._valid_field_parameter(field, name)

    loan_id = fields.Many2one(
        'hr.loan', 
        string="Préstamo", 
        required=True, 
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(
        string="Secuencia", 
        default=1,
        help="Orden de la cuota"
    )
    date_due = fields.Date(
        string="Fecha de Vencimiento", 
        required=True,
        index=True
    )
    amount = fields.Monetary(
        string="Monto", 
        required=True,
        digits=(16, 2)
    )
    currency_id = fields.Many2one(
        related='loan_id.currency_id', 
        store=True,
        string="Moneda"
    )
    paid = fields.Boolean(
        string="Pagado", 
        default=False,
        index=True
    )
    payslip_id = fields.Many2one(
        'hr.payslip', 
        string="Nómina aplicada", 
        ondelete='set null', 
        readonly=True,
        help="Nómina donde se aplicó el descuento de esta cuota"
    )
    payment_date = fields.Date(
        string="Fecha de Pago",
        readonly=True,
        help="Fecha en que se pagó la cuota"
    )
    notes = fields.Text(string="Observaciones")

    @api.constrains('amount')
    def _check_amount(self):
        """Validar que el monto sea positivo"""
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("El monto de la cuota debe ser mayor que cero."))

    @api.constrains('date_due')
    def _check_date_due(self):
        """Validar fecha de vencimiento"""
        for record in self:
            if record.loan_id and record.date_due < record.loan_id.start_date:
                raise ValidationError(_("La fecha de vencimiento no puede ser anterior a la fecha de inicio del préstamo."))

    def action_mark_paid(self):
        """Marcar cuota como pagada manualmente"""
        self.ensure_one()
        if self.paid:
            raise ValidationError(_("Esta cuota ya está marcada como pagada."))
        
        self.write({
            'paid': True,
            'payment_date': fields.Date.today(),
        })
        
        self.loan_id.message_post(
            body=_("Cuota %s marcada como pagada manualmente.") % self.sequence
        )

    def action_mark_unpaid(self):
        """Marcar cuota como no pagada"""
        self.ensure_one()
        if not self.paid:
            raise ValidationError(_("Esta cuota no está pagada."))
        
        self.write({
            'paid': False,
            'payment_date': False,
            'payslip_id': False,
        })
        
        self.loan_id.message_post(
            body=_("Cuota %s marcada como no pagada.") % self.sequence
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribir create para validaciones y batch"""
        for vals in vals_list:
            if not vals.get('sequence'):
                loan_id = vals.get('loan_id')
                if loan_id:
                    last_sequence = self.search([
                        ('loan_id', '=', loan_id)
                    ], order='sequence desc', limit=1)
                    vals['sequence'] = (last_sequence.sequence or 0) + 1
        return super().create(vals_list)

    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = _("Cuota %s - %s") % (record.sequence, record.loan_id.name)
            result.append((record.id, name))
        return result
        