from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)

class HrContractSalaryLine(models.Model):
    _name = 'hr.contract.salary.line'
    _description = 'Línea de Salario de Contrato'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string="Referencia", 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: _('Nueva Línea'),
        tracking=True
    )
    
    contract_id = fields.Many2one(
        'hr.contract', 
        string="Contrato", 
        required=True, 
        ondelete='cascade',
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
        help="Moneda en la que se establece este salario"
    )
    
    wage = fields.Monetary(
        string="Salario", 
        required=True,
        tracking=True,
        help="Salario en la moneda especificada"
    )
    
    schedule_pay = fields.Selection([
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semi-annually', 'Semestral'),
        ('annually', 'Anual'),
        ('weekly', 'Semanal'),
        ('bi-weekly', 'Quincenal'),
        ('daily', 'Diario'),
    ], string="Frecuencia de Pago", required=True, default='monthly', tracking=True)
    
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string="Estructura Salarial",
        tracking=True,
        help="Estructura salarial específica para esta línea"
    )
    
    date_start = fields.Date(
        string="Fecha de Inicio", 
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Fecha desde la cual este salario es válido"
    )
    
    date_end = fields.Date(
        string="Fecha de Fin",
        tracking=True,
        help="Fecha hasta la cual este salario es válido (dejar vacío si es indefinido)"
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('cancelled', 'Cancelado'),
    ], string="Estado", default='draft', tracking=True)
    
    is_current = fields.Boolean(
        string="¿Es Actual?",
        compute='_compute_is_current',
        store=True,
        help="Indica si esta línea está vigente actualmente"
    )
    
    notes = fields.Text(
        string="Observaciones",
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        required=True, 
        default=lambda self: self.env.company,
        tracking=True
    )
    
    wage_converted = fields.Monetary(
        string="Salario Convertido",
        compute='_compute_wage_converted',
        store=True,
        help="Salario convertido a la moneda de la empresa"
    )
    
    currency_company_id = fields.Many2one(
        'res.currency',
        string="Moneda de Empresa",
        compute='_compute_currency_company',
        store=True
    )

    @api.depends('date_start', 'date_end', 'state')
    def _compute_is_current(self):
        """Calcular si la línea está vigente actualmente"""
        today = date.today()
        for line in self:
            if line.state != 'active':
                line.is_current = False
                continue
                
            if line.date_start and line.date_start > today:
                line.is_current = False
                continue
                
            if line.date_end and line.date_end < today:
                line.is_current = False
                continue
                
            line.is_current = True

    @api.depends('wage', 'currency_id')
    def _compute_wage_converted(self):
        """Convertir salario a moneda de empresa"""
        for line in self:
            if line.wage and line.currency_id and line.company_id.currency_id:
                if line.currency_id.id == line.company_id.currency_id.id:
                    line.wage_converted = line.wage
                else:
                    try:
                        line.wage_converted = line.currency_id._convert(
                            line.wage, 
                            line.company_id.currency_id, 
                            line.company_id, 
                            date.today()
                        )
                    except Exception as e:
                        _logger.warning(f"Error convirtiendo salario: {str(e)}")
                        line.wage_converted = line.wage
            else:
                line.wage_converted = 0.0

    @api.depends('company_id')
    def _compute_currency_company(self):
        """Obtener moneda de empresa"""
        for line in self:
            line.currency_company_id = line.company_id.currency_id

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Validar fechas de vigencia"""
        for line in self:
            if line.date_start and line.date_end and line.date_start > line.date_end:
                raise ValidationError(_("La fecha de inicio no puede ser posterior a la fecha de fin."))

    @api.constrains('contract_id', 'currency_id', 'date_start', 'date_end', 'state')
    def _check_overlapping_dates(self):
        """Validar que no haya solapamiento de fechas para la misma moneda"""
        for line in self:
            if line.state != 'active':
                continue
                
            overlapping_lines = self.search([
                ('contract_id', '=', line.contract_id.id),
                ('currency_id', '=', line.currency_id.id),
                ('state', '=', 'active'),
                ('id', '!=', line.id)
            ])
            
            for other_line in overlapping_lines:

                if self._dates_overlap(line, other_line):
                    raise ValidationError(_(
                        "Existe solapamiento de fechas con la línea %s para la moneda %s"
                    ) % (other_line.name, line.currency_id.name))

    def _dates_overlap(self, line1, line2):
        """Verificar si dos líneas tienen fechas que se solapan"""
        if not line1.date_end or not line2.date_end:
            return True
            
        return not (line1.date_end < line2.date_start or line2.date_end < line1.date_start)

    @api.constrains('wage')
    def _check_wage(self):
        """Validar que el salario sea positivo"""
        for line in self:
            if line.wage <= 0:
                raise ValidationError(_("El salario debe ser mayor que cero."))

    def action_activate(self):
        """Activar la línea de salario"""
        for line in self:
            if line.state != 'draft':
                continue
            line.state = 'active'

    def action_inactivate(self):
        """Inactivar la línea de salario"""
        for line in self:
            if line.state != 'active':
                continue
            line.state = 'inactive'

    def action_cancel(self):
        """Cancelar la línea de salario"""
        for line in self:
            if line.state not in ['draft', 'active', 'inactive']:
                continue
            line.state = 'cancelled'

    def action_draft(self):
        """Volver a borrador"""
        for line in self:
            if line.state not in ['inactive', 'cancelled']:
                continue
            line.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribir create para validaciones y batch"""
        for vals in vals_list:
            if vals.get('contract_id'):
                contract = self.env['hr.contract'].browse(vals['contract_id'])
                if not contract.exists():
                    raise UserError(_("El contrato especificado no existe."))
                
                if not vals.get('company_id'):
                    vals['company_id'] = contract.company_id.id
        
        records = super().create(vals_list)
        
        for record in records:
            if record.name == _('Nueva Línea'):
                record.name = self.env['ir.sequence'].next_by_code('hr.contract.salary.line') or _('SL') + '/' + datetime.now().strftime('%Y/%m')
        
        return records

    def unlink(self):
        """Sobrescribir unlink para validaciones"""
        for record in self:
            if record.state == 'active':
                raise UserError(_("No puedes eliminar una línea de salario activa."))
        return super().unlink()

    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name} - {record.currency_id.name} ({record.wage})"
            result.append((record.id, name))
        return result

    @api.model
    def get_active_salary_line(self, contract_id, currency_id, date=None):
        
        if not date:
            date = date.today()
            
        domain = [
            ('contract_id', '=', contract_id),
            ('currency_id', '=', currency_id),
            ('state', '=', 'active'),
            ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date)
        ]
        
        return self.search(domain, limit=1, order='date_start desc')

    @api.model
    def get_salary_for_payslip(self, contract_id, currency_id, date_from, date_to):
        
        domain = [
            ('contract_id', '=', contract_id),
            ('currency_id', '=', currency_id),
            ('state', '=', 'active'),
            ('date_start', '<=', date_to),
            '|', ('date_end', '=', False), ('date_end', '>=', date_from)
        ]
        
        salary_line = self.search(domain, limit=1, order='date_start desc')
        
        if not salary_line:
            return {
                'wage': 0.0,
                'currency_id': currency_id,
                'schedule_pay': 'monthly',
                'struct_id': False,
                'salary_line_id': False
            }
        
        return {
            'wage': salary_line.wage,
            'currency_id': salary_line.currency_id.id,
            'schedule_pay': salary_line.schedule_pay,
            'struct_id': salary_line.struct_id.id if salary_line.struct_id else False,
            'salary_line_id': salary_line.id
        } 