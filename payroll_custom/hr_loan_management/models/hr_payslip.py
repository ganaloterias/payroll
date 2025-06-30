from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payslip_run_id') and not vals.get('currency_id'):
                batch = self.env['hr.payslip.run'].browse(vals['payslip_run_id'])
                if batch.currency_id:
                    vals['currency_id'] = batch.currency_id.id
        return super().create(vals_list)

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = super().get_inputs(contracts, date_from, date_to)
        
        res.extend(self._get_loan_inputs(contracts, date_from, date_to))
        
        return res

    def _get_loan_inputs(self, contracts, date_from, date_to):
        inputs = []
        
        for contract in contracts:
            employee = contract.employee_id
            if not employee:
                continue
                
            loans = self.env['hr.loan'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['approved', 'running']),
                ('company_id', '=', contract.company_id.id),
            ])
            
            for loan in loans:
                if loan.currency_id.id != contract.company_id.currency_id.id:
                    _logger.warning(
                        "Moneda del préstamo %s no coincide con la moneda de la empresa %s",
                        loan.name, contract.company_id.name
                    )
                    continue
                
                installments = self.env['hr.loan.installment'].search([
                    ('loan_id', '=', loan.id),
                    ('date_due', '>=', date_from),
                    ('date_due', '<=', date_to),
                    ('paid', '=', False),
                ], limit=1)
                
                if installments:
                    inputs.append({
                        'name': _('Descuento por Préstamo - %s') % loan.name,
                        'code': 'PRESTAMO',
                        'contract_id': contract.id,
                        'amount': installments.amount,
                        'loan_installment_id': installments.id,
                    })
        
        return inputs

    @api.onchange('employee_id', 'date_from', 'date_to', 'struct_id')
    def onchange_employee(self):
        result = super().onchange_employee()
        
        if not self.employee_id or not self.date_from or not self.date_to:
            return result
        
        if self.contract_id:
            self._add_loan_inputs_onchange()
        
        return result
    
    def _add_loan_inputs_onchange(self):
        self.ensure_one()
        
        try:
            existing_inputs = self.input_line_ids.filtered(
                lambda line: line.code == 'PRESTAMO'
            )
            if existing_inputs:
                self.input_line_ids = [(2, input_id) for input_id in existing_inputs.ids]
            
            loan_inputs = self._get_loan_inputs([self.contract_id], self.date_from, self.date_to)
            
            for input_data in loan_inputs:
                self.input_line_ids = [(0, 0, input_data)]
                
        except Exception as e:
            _logger.error("Error al añadir inputs de préstamos: %s", str(e))

    def compute_sheet(self):
        for payslip in self:
            if payslip.contract_id:
                payslip._add_loan_inputs_onchange()
        
        return super().compute_sheet()

    def action_payslip_done(self):
        res = super().action_payslip_done()

        for payslip in self:
            payslip._process_loan_payments()

        return res

    def _process_loan_payments(self):
        self.ensure_one()
        
        try:
            loan_inputs = self.input_line_ids.filtered(
                lambda line: line.code == 'PRESTAMO' and line.amount > 0
            )
            
            for input_line in loan_inputs:
                installment_id = input_line.loan_installment_id.id if input_line.loan_installment_id else False
                
                if installment_id:
                    installment = self.env['hr.loan.installment'].browse(installment_id)
                    if installment.exists() and not installment.paid:
                        installment.write({
                            'paid': True,
                            'payslip_id': self.id,
                            'payment_date': self.date_to,
                        })
                        
                        self.message_post(
                            body=_("Cuota de préstamo %s marcada como pagada.") % installment.sequence
                        )
                else:
                    installments = self.env['hr.loan.installment'].search([
                        ('loan_id.employee_id', '=', self.employee_id.id),
                        ('date_due', '>=', self.date_from),
                        ('date_due', '<=', self.date_to),
                        ('paid', '=', False)
                    ], limit=1)
                    
                    if installments:
                        installments.write({
                            'paid': True,
                            'payslip_id': self.id,
                            'payment_date': self.date_to,
                        })
                        
                        self.message_post(
                            body=_("Cuota de préstamo marcada como pagada automáticamente.")
                        )
                        
        except Exception as e:
            _logger.error("Error al procesar pagos de préstamos: %s", str(e))
            raise UserError(_("Error al procesar pagos de préstamos: %s") % str(e))

    def action_payslip_cancel(self):
        for payslip in self:
            payslip._revert_loan_payments()
        
        return super().action_payslip_cancel()

    def _revert_loan_payments(self):
        self.ensure_one()
        
        try:
            installments = self.env['hr.loan.installment'].search([
                ('payslip_id', '=', self.id),
                ('paid', '=', True)
            ])
            
            for installment in installments:
                installment.write({
                    'paid': False,
                    'payslip_id': False,
                    'payment_date': False,
                })
                
            if installments:
                self.message_post(
                    body=_("Se han revertido %s cuotas de préstamo al cancelar la nómina.") % len(installments)
                )
                
        except Exception as e:
            _logger.error("Error al revertir pagos de préstamos: %s", str(e))


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    
    loan_installment_id = fields.Many2one(
        'hr.loan.installment', 
        string='Cuota de préstamo',
        help='Cuota de préstamo asociada a esta entrada de nómina',
        ondelete='set null'
    )
    
    @api.constrains('amount', 'loan_installment_id')
    def _check_loan_amount(self):
        for record in self:
            if record.loan_installment_id and record.amount != record.loan_installment_id.amount:
                raise UserError(_(
                    "El monto del input (%s) no coincide con el monto de la cuota (%s)."
                ) % (record.amount, record.loan_installment_id.amount))
