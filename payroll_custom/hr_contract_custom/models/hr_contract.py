from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class HrContract(models.Model):
    _inherit = "hr.contract"
    
    salary_line_ids = fields.One2many(
        'hr.contract.salary.line',
        'contract_id',
        string="Líneas de Salario",
        copy=True,
        help="Líneas de salario multimoneda para este contrato"
    )
    
    current_salary_lines_count = fields.Integer(
        string="Líneas Activas",
        compute='_compute_salary_lines_count',
        store=True
    )
    
    currencies_count = fields.Integer(
        string="Monedas",
        compute='_compute_currencies_count',
        store=True
    )
    
    auto_select_salary = fields.Boolean(
        string="Selección Automática de Salario",
        default=True,
        help="Si está marcado, se seleccionará automáticamente el salario según la moneda de la nómina"
    )

    @api.depends('salary_line_ids.state')
    def _compute_salary_lines_count(self):
        for contract in self:
            contract.current_salary_lines_count = len(
                contract.salary_line_ids.filtered(lambda line: line.state == 'active')
            )

    @api.depends('salary_line_ids.currency_id')
    def _compute_currencies_count(self):
        for contract in self:
            currencies = contract.salary_line_ids.mapped('currency_id')
            contract.currencies_count = len(currencies)

    @api.model
    def get_salary_for_currency(self, contract_id, currency_id, date=None):
        
        if not date:
            date = fields.Date.today()
            
        return self.env['hr.contract.salary.line'].get_active_salary_line(
            contract_id, currency_id, date
        )

    @api.model
    def get_salary_for_payslip(self, contract_id, currency_id, date_from, date_to):
        
        return self.env['hr.contract.salary.line'].get_salary_for_payslip(
            contract_id, currency_id, date_from, date_to
        )

    def action_view_salary_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Líneas de Salario'),
            'res_model': 'hr.contract.salary.line',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }

    def action_create_salary_line(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Línea de Salario'),
            'res_model': 'hr.contract.salary.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }

    def action_migrate_existing_salary(self):
        self.ensure_one()
        
        if not self.wage or self.wage <= 0:
            raise UserError(_("No hay salario existente para migrar."))
        
        existing_line = self.env['hr.contract.salary.line'].search([
            ('contract_id', '=', self.id),
            ('currency_id', '=', self.company_id.currency_id.id),
            ('state', '=', 'active')
        ], limit=1)
        
        if existing_line:
            raise UserError(_("Ya existe una línea de salario activa para la moneda %s.") % self.company_id.currency_id.name)
        
        salary_line = self.env['hr.contract.salary.line'].create({
            'contract_id': self.id,
            'currency_id': self.company_id.currency_id.id,
            'wage': self.wage,
            'schedule_pay': self.schedule_pay or 'monthly',
            'struct_id': self.structure_type_id.default_struct_id.id if self.structure_type_id else False,
            'date_start': self.date_start or fields.Date.today(),
            'state': 'active',
            'company_id': self.company_id.id,
            'notes': _("Migrado desde salario existente del contrato")
        })
        
        self.message_post(
            body=_("Salario migrado a nueva estructura multimoneda: %s") % salary_line.name
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Línea de Salario Creada'),
            'res_model': 'hr.contract.salary.line',
            'res_id': salary_line.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        
        for contract in contracts:
            if contract.wage and contract.wage > 0:
                try:
                    contract.action_migrate_existing_salary()
                except Exception as e:
                    _logger.warning(f"No se pudo migrar salario para contrato {contract.name}: {str(e)}")
        
        return contracts

    def write(self, vals):
        if 'wage' in vals and vals['wage'] and vals['wage'] > 0:
            for contract in self:
                try:
                    existing_line = self.env['hr.contract.salary.line'].search([
                        ('contract_id', '=', contract.id),
                        ('currency_id', '=', contract.company_id.currency_id.id),
                        ('state', '=', 'active')
                    ], limit=1)
                    
                    if existing_line:
                        existing_line.write({
                            'wage': vals['wage'],
                            'notes': _("Actualizado desde contrato - %s") % fields.Date.today()
                        })
                    else:
                        self.env['hr.contract.salary.line'].create({
                            'contract_id': contract.id,
                            'currency_id': contract.company_id.currency_id.id,
                            'wage': vals['wage'],
                            'schedule_pay': vals.get('schedule_pay', contract.schedule_pay) or 'monthly',
                            'struct_id': vals.get('structure_type_id', contract.structure_type_id.id) and 
                                       self.env['hr.contract'].browse(vals['structure_type_id']).default_struct_id.id or
                                       (contract.structure_type_id.default_struct_id.id if contract.structure_type_id else False),
                            'date_start': fields.Date.today(),
                            'state': 'active',
                            'company_id': contract.company_id.id,
                            'notes': _("Creado desde cambio de contrato")
                        })
                        
                except Exception as e:
                    _logger.warning(f"No se pudo actualizar salario para contrato {contract.name}: {str(e)}")
        
        return super().write(vals)

    def get_current_salary(self, currency_id=None):
        
        self.ensure_one()
        
        if not currency_id:
            currency_id = self.company_id.currency_id.id
        
        salary_line = self.get_salary_for_currency(self.id, currency_id)
        
        if salary_line:
            return salary_line.wage
        else:
            if currency_id == self.company_id.currency_id.id:
                return self.wage or 0.0
            else:
                return 0.0

    def get_all_active_salaries(self):
       
        self.ensure_one()
        
        active_lines = self.salary_line_ids.filtered(lambda line: line.state == 'active')
        
        salaries = []
        for line in active_lines:
            salaries.append({
                'currency_id': line.currency_id.id,
                'currency_name': line.currency_id.name,
                'wage': line.wage,
                'wage_converted': line.wage_converted,
                'schedule_pay': line.schedule_pay,
                'date_start': line.date_start,
                'date_end': line.date_end,
                'is_current': line.is_current,
                'salary_line_id': line.id
            })
        
        return salaries 