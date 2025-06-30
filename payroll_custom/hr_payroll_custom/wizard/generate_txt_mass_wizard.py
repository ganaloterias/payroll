import base64
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class GenerateTxtMassWizard(models.TransientModel):
    _name = 'generate.txt.mass.wizard'
    _description = 'Generador masivo de archivo TXT a partir de nóminas seleccionadas por período'

    date_from = fields.Date(string="Fecha Inicial", required=True)
    date_to = fields.Date(string="Fecha Final", required=True)
    payment_date = fields.Date(string="Fecha de Pago", required=True,
                               default=lambda self: fields.Date.context_today(self))

    payslip_count = fields.Integer(string="Número de Nóminas", compute='_compute_payslip_count')
    total_amount = fields.Monetary(string="Monto Total", compute='_compute_total_amount')
    currency_id = fields.Many2one('res.currency', string="Moneda", 
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('date_from', 'date_to')
    def _compute_payslip_count(self):
        for record in self:
            if record.date_from and record.date_to:
                record.payslip_count = self.env['hr.payslip'].search_count([
                    ('date_to', '>=', record.date_from),
                    ('date_to', '<=', record.date_to),
                    ('state', '=', 'done')
                ])
            else:
                record.payslip_count = 0

    @api.depends('date_from', 'date_to')
    def _compute_total_amount(self):
        for record in self:
            if record.date_from and record.date_to:
                payslips = self.env['hr.payslip'].search([
                    ('date_to', '>=', record.date_from),
                    ('date_to', '<=', record.date_to),
                    ('state', '=', 'done')
                ])
                record.total_amount = sum(
                    payslips.mapped('line_ids').filtered(lambda l: l.code == 'NET').mapped('total')
                )
            else:
                record.total_amount = 0.0

    def _validate_company_data(self, company, partner):
        errors = []
        
        if not company.vat:
            errors.append(_("La empresa debe tener RIF asignado."))
        
        if not partner.ordenante_account_number or len(partner.ordenante_account_number) != 20:
            errors.append(_("La cuenta bancaria de la empresa ordenante debe tener 20 dígitos."))
        
        if not company.name or len(company.name) < 3:
            errors.append(_("El nombre de la empresa ordenante debe tener al menos 3 caracteres."))
        
        if errors:
            raise UserError("\n".join(errors))
        
        return True

    def _validate_employee_data(self, employee, bank):
        if not bank or not bank.acc_number or len(bank.acc_number) != 20:
            raise UserError(_("El empleado %s no tiene una cuenta bancaria válida de 20 dígitos.") % employee.name)
        
        rif_emp_raw = employee.identification_id or ""
        if len(rif_emp_raw.replace(" ", "").replace("-", "")) < 4:
            raise UserError(_("El RIF del empleado %s debe tener al menos 4 dígitos.") % employee.name)
        
        return True

    def _get_company_header_data(self, company, partner):
        self._validate_company_data(company, partner)
        
        rif_letter, rif_number = self._extract_rif_parts(company.vat)
        rif_company = rif_letter + rif_number.zfill(9)
        
        return {
            'number_negotiation': (partner.number_negotiation or "334885").zfill(8),
            'ref_lot': (partner.ref_lot or "2").zfill(8),
            'rif_company': rif_company,
            'account_company': partner.ordenante_account_number,
            'type_account': {'corriente': '00', 'ahorro': '01'}.get(partner.type_account, '00'),
            'company_name': company.name.upper()[:35].ljust(35, ' '),
            'payment_date_str': self.payment_date.strftime("%d/%m/%Y")
        }

    def _extract_rif_parts(self, rif):
        if not rif:
            return ("", "")
        rif_clean = rif.replace(" ", "").replace("-", "")
        if rif_clean and rif_clean[0].isalpha():
            return rif_clean[0], rif_clean[1:]
        return ("", rif_clean)

    def _format_field(self, value, length, align='left', fillchar=' '):
        if not value:
            value = ""
        value = str(value)
        if len(value) > length:
            value = value[:length]
        return value.ljust(length, fillchar) if align == 'left' else value.zfill(length)

    def _format_amount(self, amount):
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0.0
        formatted = f"{amount:0.2f}".replace('.', ',')
        return formatted.zfill(15)

    def _get_employee_transaction_data(self, payslip, header_data, secuencia):
        employee = payslip.employee_id
        bank = employee.bank_account_id
        
        self._validate_employee_data(employee, bank)
        
        net_salary = sum(payslip.line_ids.filtered(lambda l: l.code == 'NET').mapped('total'))
        
        rif_emp_raw = employee.identification_id.replace(" ", "").replace("-", "")
        if rif_emp_raw[0].isalpha():
            emp_letter, emp_number = self._extract_rif_parts(rif_emp_raw)
        else:
            emp_letter = "V"
            emp_number = rif_emp_raw
        emp_number = emp_number.zfill(9)
        
        formatted_amount = self._format_amount(net_salary)
        
        return {
            'net_salary': net_salary,
            'formatted_amount': formatted_amount,
            'emp_letter': emp_letter,
            'emp_number': emp_number,
            'employee_name': employee.name.upper(),
            'bank_account': bank.acc_number,
            'bank_bic': bank.bank_id.bic or "BSCHVECA",
            'secuencia': secuencia
        }

    def _generate_transaction_lines(self, payslips, header_data):
        transaction_lines = []
        total_amount = 0.0
        
        payslips.mapped('employee_id.bank_account_id.bank_id')
        
        for secuencia, payslip in enumerate(payslips, 1):
            try:
                transaction_data = self._get_employee_transaction_data(payslip, header_data, secuencia)
                total_amount += transaction_data['net_salary']
                
                debit_line = (
                    "DEBITO  " +
                    self._format_field(str(secuencia), 8, align='right', fillchar='0') +
                    header_data['rif_company'] +
                    header_data['company_name'] +
                    header_data['payment_date_str'] +
                    header_data['type_account'] +
                    header_data['account_company'] +
                    transaction_data['formatted_amount'] +
                    "VEB40"
                )
                
                credit_line = (
                    "CREDITO " +
                    self._format_field(str(secuencia), 8, align='right', fillchar='0') +
                    transaction_data['emp_letter'] + transaction_data['emp_number'] +
                    self._format_field(transaction_data['employee_name'], 30) +
                    "00" +
                    transaction_data['bank_account'] +
                    transaction_data['formatted_amount'] +
                    "10" +
                    self._format_field(transaction_data['bank_bic'], 10)
                )
                
                transaction_lines.extend([debit_line, credit_line])
                
            except Exception as e:
                _logger.error(f"Error procesando nómina {payslip.name}: {str(e)}")
                raise UserError(_("Error procesando nómina %s: %s") % (payslip.name, str(e)))
        
        return transaction_lines, total_amount

    def action_generate_txt(self):
        self.ensure_one()
        
        if self.date_from > self.date_to:
            raise UserError(_("La fecha inicial no puede ser posterior a la fecha final."))
        
        payslips = self.env['hr.payslip'].search([
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done')
        ])
        
        if not payslips:
            raise UserError(_("No se encontraron nóminas procesadas en el período seleccionado."))
        
        if len(payslips) > 1000:
            raise UserError(_("No se pueden procesar más de 1000 nóminas a la vez por rendimiento."))
        
        try:
            company = self.env.company
            partner = company.partner_id
            
            header_data = self._get_company_header_data(company, partner)
            
            header = (
                "HEADER  " +
                header_data['ref_lot'] +
                header_data['number_negotiation'] +
                header_data['rif_company'] +
                header_data['payment_date_str'] +
                header_data['payment_date_str']
            )
            
            transaction_lines, total_amount = self._generate_transaction_lines(payslips, header_data)
            
            num_lines = len(payslips)
            formatted_total_amount = self._format_amount(total_amount)
            
            total_line = (
                "TOTAL   " +
                self._format_field(str(num_lines), 5, align='right', fillchar='0') +
                self._format_field(str(num_lines), 5, align='right', fillchar='0') +
                formatted_total_amount
            )
            
            txt_content = header + "\n" + "\n".join(transaction_lines) + "\n" + total_line + "\n"
            txt_data = base64.b64encode(txt_content.encode("utf-8"))
            
            attachment = self.env['ir.attachment'].create({
                'name': f"NOMINAS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                'datas': txt_data,
                'type': 'binary',
                'res_model': 'generate.txt.mass.wizard',
                'res_id': self.id,
            })
            
            _logger.info(f"Archivo TXT generado exitosamente: {attachment.name} con {len(payslips)} nóminas")
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'new',
            }
            
        except Exception as e:
            _logger.error(f"Error generando archivo TXT: {str(e)}")
            raise UserError(_("Error generando archivo TXT: %s") % str(e))