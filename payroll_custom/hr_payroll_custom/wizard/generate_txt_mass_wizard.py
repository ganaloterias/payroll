import base64
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GenerateTxtMassWizard(models.TransientModel):
    _name = 'generate.txt.mass.wizard'
    _description = 'Generador masivo de archivo TXT a partir de nóminas seleccionadas por período'

    date_from = fields.Date(string="Fecha Inicial", required=True)
    date_to = fields.Date(string="Fecha Final", required=True)
    payment_date = fields.Date(string="Fecha de Pago", required=True,
                               default=lambda self: fields.Date.context_today(self))


    def format_field(self, value, length, align='left', fillchar=' '):
        if not value:
            value = ""
        value = str(value)
        if len(value) > length:
            value = value[:length]
        return value.ljust(length, fillchar) if align == 'left' else value.zfill(length)

    def format_amount(self, amount):
        """
        Formatea el monto a 15 caracteres con dos decimales y separador de coma.
        Ejemplo: 100,00 -> "000000000000000100,00"
        """
        try:
            amount = float(amount)
        except ValueError:
            amount = 0.0
        formatted = f"{amount:0.2f}".replace('.', ',')
        return formatted.zfill(15)

    def extract_rif_parts(self, rif):
        """
        Extrae la letra y el número del RIF, asumiendo que el RIF inicia con una letra.
        Ejemplo: "J503979470" -> ("J", "503979470")
        """
        if not rif:
            return ("", "")
        rif = rif.replace(" ", "").replace("-", "")
        if rif[0].isalpha():
            return rif[0], rif[1:]
        else:
            return ("", rif)

    def action_generate_txt(self):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('date_to', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done')
        ])
        if not payslips:
            raise UserError(_("No se encontraron nóminas procesadas en el período seleccionado."))

        company = self.env.company
        partner = company.partner_id
        
        number_negotiation = (partner.number_negotiation or "334885").zfill(8)
        ref_lot = partner.ref_lot or "2"
        if len(ref_lot) > 8:
            raise UserError(_("La referencia de lote no puede exceder 8 dígitos."))
        ref_lot = ref_lot.zfill(8)

        if not company.vat:
            raise UserError(_("La empresa debe tener RIF asignado."))
        rif_letter, rif_number = self.extract_rif_parts(company.vat)
        if len(rif_number) < 4:
            raise UserError(_("El número del RIF de la empresa debe tener al menos 4 dígitos."))
        if not rif_letter:
            raise UserError(_("El RIF de la empresa debe iniciar con una letra."))
        rif_company = rif_letter + rif_number
        if len(rif_company) < 10:
            raise UserError(_("El RIF de la empresa debe tener al menos 10 caracteres."))

        account_company = partner.ordenante_account_number or "00000000000000000000"
        if len(account_company) != 20:
            raise UserError(_("La cuenta bancaria de la empresa ordenante debe tener 20 dígitos."))

        account_type_map = {'corriente': '00', 'ahorro': '01'}
        type_account = account_type_map.get(partner.type_account, '00')

        company_name = company.name.upper() if company.name and len(company.name) >= 3 else ""
        if not company_name:
            raise UserError(_("El nombre de la empresa ordenante debe tener al menos 3 caracteres."))
        company_name = company_name[:35].ljust(35, ' ')

        payment_date_str = self.payment_date.strftime("%d/%m/%Y")

        header = (
            "HEADER  " +
            ref_lot +
            number_negotiation +
            rif_company +
            payment_date_str +
            payment_date_str
        )
        
        transaction_lines = []
        secuencia = 1
        total_amount = 0.0

        for payslip in payslips:
            employee = payslip.employee_id
            bank = employee.bank_account_id
            if not bank or not bank.acc_number or len(bank.acc_number) != 20:
                raise UserError(_("El empleado %s no tiene una cuenta bancaria válida de 20 dígitos." % employee.name))

            rif_emp_raw = employee.identification_id or ""
            rif_emp_raw = rif_emp_raw.replace(" ", "").replace("-", "")
            if len(rif_emp_raw) < 4:
                raise UserError(_("El RIF del empleado %s debe tener al menos 4 dígitos." % employee.name))
            if rif_emp_raw[0].isalpha():
                emp_letter, emp_number = self.extract_rif_parts(rif_emp_raw)
            else:
                emp_letter = "V"
                emp_number = rif_emp_raw
            emp_number = emp_number.zfill(9)

            net_salary = sum(payslip.line_ids.filtered(lambda l: l.code == 'NET').mapped('total'))
            total_amount += net_salary
            formatted_amount = self.format_amount(net_salary)

            debit_line = (
                "DEBITO  " +
                self.format_field(str(secuencia), 8, align='right', fillchar='0') +
                rif_company +
                company_name +
                payment_date_str +
                type_account +
                account_company +
                formatted_amount +
                "VEB40"
            )
            transaction_lines.append(debit_line)
            credit_line = (
                "CREDITO " +
                self.format_field(str(secuencia), 8, align='right', fillchar='0') +
                emp_letter + emp_number +
                self.format_field(employee.name.upper(), 30) +
                "00" +
                bank.acc_number +
                formatted_amount +
                "10" +
                self.format_field(bank.bank_id.bic or "BSCHVECA", 10)
            )
            transaction_lines.append(credit_line)
            secuencia += 1

        num_lines = len(payslips)
        formatted_total_amount = self.format_amount(total_amount)

        total_line = (
            "TOTAL   " +
            self.format_field(str(num_lines), 5, align='right', fillchar='0') +
            self.format_field(str(num_lines), 5, align='right', fillchar='0') +
            formatted_total_amount
        )

        txt_content = header + "\n" + "\n".join(transaction_lines) + "\n" + total_line + "\n"
        txt_data = base64.b64encode(txt_content.encode("utf-8"))

        attachment = self.env['ir.attachment'].create({
            'name': "NOMINAS_%s.txt" % datetime.now().strftime("%Y%m%d_%H%M%S"),
            'datas': txt_data,
            'type': 'binary',
            'res_model': 'generate.txt.mass.wizard',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }