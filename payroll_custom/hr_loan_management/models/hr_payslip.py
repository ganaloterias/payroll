from odoo import api, fields, models


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
        # Llamamos al método original para obtener los inputs base
        res = super().get_inputs(contracts, date_from, date_to)

        # El resto del código para añadir entradas de préstamos
        # se traslada al método onchange_employee
        return res

    @api.onchange('employee_id', 'date_from', 'date_to', 'struct_id')
    def onchange_employee(self):
        # Primero ejecutamos el método original
        result = super().onchange_employee()
        
        # Si no tenemos empleado o fechas, no continuamos
        if not self.employee_id or not self.date_from or not self.date_to:
            return result
            
        # Ahora añadimos los préstamos
        self._add_loan_inputs()
        
        return result
    
    def _add_loan_inputs(self):
        """Añade entradas de préstamos a la nómina actual"""
        self.ensure_one()
        
        # Si no hay contrato o empleado, salimos
        if not self.contract_id or not self.employee_id:
            return
            
        loan_obj = self.env['hr.loan']
        installment_obj = self.env['hr.loan.installment']
        
        # Buscar préstamos en estado aprobado o en curso
        loans = loan_obj.search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['approved', 'running']),
        ])
        
        for loan in loans:
            # Buscar cuotas pendientes que caen dentro del período de la nómina
            installments = installment_obj.search([
                ('loan_id', '=', loan.id),
                ('date_due', '>=', self.date_from),
                ('date_due', '<=', self.date_to),
                ('paid', '=', False),
            ], limit=1)  # Limitamos a una cuota por periodo de nómina
            
            if installments:
                # Verificar si ya existe una entrada con este código
                existing_input = self.input_line_ids.filtered(
                    lambda line: line.code == 'PRESTAMO'
                )
                
                # Si estamos en un onchange, debemos crear las líneas en memoria, no en la base de datos
                if self.id:  # Si la nómina ya existe en la base de datos
                    if existing_input:
                        # Si ya existe, actualizamos el monto
                        existing_input.write({
                            'amount': installments.amount,
                            'loan_installment_id': installments.id,
                        })
                    else:
                        # Crear nueva entrada en la BD
                        self.env['hr.payslip.input'].create({
                            'name': 'Descuento por Préstamo',
                            'code': 'PRESTAMO',
                            'amount': installments.amount,
                            'contract_id': self.contract_id.id,
                            'payslip_id': self.id,
                            'loan_installment_id': installments.id,
                        })
                else:  # Si la nómina no existe aún (estamos en onchange)
                    if existing_input:
                        # Actualizamos la línea virtual
                        existing_input.amount = installments.amount
                        existing_input.loan_installment_id = installments.id
                    else:
                        # Crear una línea de entrada virtual para el onchange
                        input_line_vals = {
                            'name': 'Descuento por Préstamo',
                            'code': 'PRESTAMO',
                            'amount': installments.amount,
                            'contract_id': self.contract_id.id,
                            'loan_installment_id': installments.id,
                        }
                        # Añadir a las líneas de entrada existentes
                        self.update({
                            'input_line_ids': [(0, 0, input_line_vals)]
                        })

    def compute_sheet(self):
        # Asegurarse de que las entradas de préstamos están presentes antes de calcular
        for payslip in self:
            payslip._add_loan_inputs()
        return super().compute_sheet()

    def action_payslip_done(self):
        # Llamar al método original primero
        res = super().action_payslip_done()

        # Buscar los inputs relacionados con préstamos
        for payslip in self:
            loan_inputs = payslip.input_line_ids.filtered(lambda line: line.code == 'PRESTAMO' and line.amount > 0)
            
            for input_line in loan_inputs:
                # Extraer el ID de la cuota (si se estableció)
                installment_id = input_line.loan_installment_id.id if input_line.loan_installment_id else False
                
                if installment_id:
                    # Actualizar la cuota específica
                    installment = self.env['hr.loan.installment'].browse(installment_id)
                    if installment.exists() and not installment.paid:
                        installment.write({
                            'paid': True,
                            'payslip_id': payslip.id,
                        })
                else:
                    # Buscar cuotas por fecha si no tenemos el ID específico
                    installments = self.env['hr.loan.installment'].search([
                        ('loan_id.employee_id', '=', payslip.employee_id.id),
                        ('date_due', '>=', payslip.date_from),
                        ('date_due', '<=', payslip.date_to),
                        ('paid', '=', False)
                    ], limit=1)
                    
                    if installments:
                        installments.write({
                            'paid': True,
                            'payslip_id': payslip.id,
                        })

        return res


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    
    loan_installment_id = fields.Many2one('hr.loan.installment', string='Cuota de préstamo', 
                                          help='Cuota de préstamo asociada a esta entrada de nómina')
