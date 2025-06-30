# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)

class HrLiquidation(models.Model):
    _name = 'hr.liquidation'
    _description = 'Liquidación de Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_end desc, name desc'
    
    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default=lambda self: _('Nuevo'), tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, domain=[('active', '=', True)], tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato', compute='_compute_contract_info', store=True)
    liquidation_type = fields.Selection([
        ('resignation', 'Renuncia'),
        ('dismissal', 'Despido'),
        ('contract_end', 'Fin de Contrato'),
        ('mutual_agreement', 'Acuerdo Mutuo')
    ], string='Tipo de Liquidación', required=True, tracking=True)
    
    date_start = fields.Date(string='Fecha Inicio', required=True, tracking=True)
    date_end = fields.Date(string='Fecha Fin', required=True, tracking=True)
    
    work_period_years = fields.Float(string='Años de Servicio', compute='_compute_work_period', store=True, digits=(16, 2))
    work_period_months = fields.Integer(string='Meses de Servicio', compute='_compute_work_period', store=True)
    work_period_days = fields.Integer(string='Días de Servicio', compute='_compute_work_period', store=True)
    
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, default=lambda self: self.env.company.currency_id, tracking=True)
    last_wage = fields.Monetary(string='Último Salario', required=True, tracking=True)
    salary_daily = fields.Monetary(string='Salario Diario', compute='_compute_salary_daily', store=True)
    
    prestaciones_monto = fields.Monetary(string='Prestaciones Sociales', compute='_compute_liquidation_amounts', store=True)
    vacaciones_monto = fields.Monetary(string='Vacaciones', compute='_compute_liquidation_amounts', store=True)
    bono_vacacional_monto = fields.Monetary(string='Bono Vacacional', compute='_compute_liquidation_amounts', store=True)
    preaviso_monto = fields.Monetary(string='Preaviso', compute='_compute_liquidation_amounts', store=True)
    total_liquidacion = fields.Monetary(string='Total Liquidación', compute='_compute_liquidation_amounts', store=True)
    
    calculation_details = fields.Text(string='Detalles del Cálculo', compute='_compute_calculation_details', store=True)
    line_ids = fields.One2many('hr.liquidation.line', 'liquidation_id', string='Líneas de Liquidación', copy=True)
    last_slip_id = fields.Many2one('hr.payslip', string='Última Nómina', compute='_compute_last_slip', store=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('done', 'Finalizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True, copy=False)
    
    created_by = fields.Many2one('res.users', string='Creado por', default=lambda self: self.env.user, readonly=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Aprobado por', readonly=True, tracking=True)
    validated_date = fields.Datetime(string='Fecha de Validación', readonly=True, tracking=True)
    done_date = fields.Datetime(string='Fecha de Finalización', readonly=True, tracking=True)
    
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, tracking=True)
    notes = fields.Text(string='Observaciones', tracking=True)
    
    @api.depends('employee_id', 'date_start', 'date_end')
    def _compute_contract_info(self):
        for record in self:
            if record.employee_id and record.date_end:
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', '=', 'open'),
                    ('company_id', '=', record.company_id.id)
                ], limit=1)
                record.contract_id = contract.id if contract else False
                if contract and not record.date_start:
                    record.date_start = contract.date_start
                if contract and not record.last_wage:
                    record.last_wage = contract.wage
                if contract and not record.currency_id:
                    record.currency_id = contract.company_id.currency_id.id
    
    @api.depends('date_start', 'date_end')
    def _compute_work_period(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                total_days = delta.days + 1
                years = total_days // 365
                remaining_days = total_days % 365
                months = remaining_days // 30
                days = remaining_days % 30
                record.work_period_years = years + (months / 12.0) + (days / 365.0)
                record.work_period_months = months
                record.work_period_days = days
            else:
                record.work_period_years = 0.0
                record.work_period_months = 0
                record.work_period_days = 0
    
    @api.depends('last_wage')
    def _compute_salary_daily(self):
        for record in self:
            record.salary_daily = record.last_wage / 30.0 if record.last_wage else 0.0
    
    @api.depends('work_period_years', 'salary_daily', 'liquidation_type')
    def _compute_liquidation_amounts(self):
        for record in self:
            if not record.salary_daily or not record.work_period_years:
                record.prestaciones_monto = 0.0
                record.vacaciones_monto = 0.0
                record.bono_vacacional_monto = 0.0
                record.preaviso_monto = 0.0
                record.total_liquidacion = 0.0
                continue
            
            calculator = self.env['hr.liquidation.calculator']
            work_period = {
                'total_days': int(record.work_period_years * 365),
                'years': int(record.work_period_years),
                'months': record.work_period_months,
                'daily_factor': 30.0
            }
            
            vacation = calculator.calculate_vacation(work_period, record.salary_daily)
            record.vacaciones_monto = vacation['amount']
            
            vacation_bonus = calculator.calculate_vacation_bonus(vacation['days'], record.salary_daily)
            record.bono_vacacional_monto = vacation_bonus['amount']
            
            social_benefits = calculator.calculate_social_benefits(work_period, record.salary_daily)
            record.prestaciones_monto = social_benefits['final_amount']
            
            if record.liquidation_type == 'dismissal':
                notice = calculator.calculate_notice(work_period, record.salary_daily)
                record.preaviso_monto = notice['amount']
            else:
                record.preaviso_monto = 0.0
            
            record.total_liquidacion = (
                record.prestaciones_monto + record.vacaciones_monto + 
                record.bono_vacacional_monto + record.preaviso_monto
            )
    
    @api.depends('prestaciones_monto', 'vacaciones_monto', 'bono_vacacional_monto', 'preaviso_monto')
    def _compute_calculation_details(self):
        for record in self:
            details = []
            details.append(f"Período de trabajo: {record.work_period_years:.2f} años")
            details.append(f"Salario diario: {record.currency_id.symbol} {record.salary_daily:.2f}")
            details.append("")
            details.append("Desglose de montos:")
            details.append(f"- Prestaciones sociales: {record.currency_id.symbol} {record.prestaciones_monto:.2f}")
            details.append(f"- Vacaciones no gozadas: {record.currency_id.symbol} {record.vacaciones_monto:.2f}")
            details.append(f"- Bono vacacional: {record.currency_id.symbol} {record.bono_vacacional_monto:.2f}")
            if record.preaviso_monto > 0:
                details.append(f"- Preaviso: {record.currency_id.symbol} {record.preaviso_monto:.2f}")
            details.append("")
            details.append(f"TOTAL: {record.currency_id.symbol} {record.total_liquidacion:.2f}")
            record.calculation_details = "\n".join(details)
    
    @api.depends('employee_id', 'date_end')
    def _compute_last_slip(self):
        for record in self:
            if record.employee_id and record.date_end:
                slip = self.env['hr.payslip'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', '=', 'done'),
                    ('date_to', '<=', record.date_end)
                ], order='date_to desc', limit=1)
                record.last_slip_id = slip.id if slip else False
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end:
                if record.date_end <= record.date_start:
                    raise ValidationError(_('La fecha de fin debe ser posterior a la fecha de inicio.'))
                if record.date_end > date.today():
                    raise ValidationError(_('La fecha de fin no puede ser futura.'))

    @api.constrains('employee_id', 'state')
    def _check_employee_liquidation(self):
        for record in self:
            if record.employee_id and record.state in ['draft', 'validated']:
                existing = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', 'in', ['draft', 'validated']),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Ya existe una liquidación activa para el empleado %s.') % record.employee_id.name)

    def action_validate(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Solo se pueden validar liquidaciones en estado borrador.'))
            
            if not record.employee_id or not record.date_start or not record.date_end:
                raise UserError(_('Debe especificar empleado y fechas.'))
            if record.total_liquidacion <= 0:
                raise UserError(_('El total de la liquidación debe ser mayor a cero.'))
            
            record.state = 'validated'
            record.approved_by = self.env.user
            record.validated_date = fields.Datetime.now()
            record._create_liquidation_lines()
            record.message_post(body=_('Liquidación validada por %s') % self.env.user.name)

    def action_done(self):
        for record in self:
            if record.state != 'validated':
                raise UserError(_('Solo se pueden finalizar liquidaciones validadas.'))
            record.state = 'done'
            record.done_date = fields.Datetime.now()
            record.message_post(body=_('Liquidación finalizada por %s') % self.env.user.name)
    
    def action_cancel(self):
        for record in self:
            if record.state not in ['draft', 'validated']:
                raise UserError(_('Solo se pueden cancelar liquidaciones en borrador o validadas.'))
            record.state = 'cancelled'
            record.message_post(body=_('Liquidación cancelada por %s') % self.env.user.name)
    
    def action_draft(self):
        for record in self:
            if record.state not in ['validated', 'cancelled']:
                raise UserError(_('Solo se puede volver a borrador desde estados validado o cancelado.'))
            record.state = 'draft'
            record.approved_by = False
            record.validated_date = False
            record.done_date = False
            record.message_post(body=_('Liquidación devuelta a borrador por %s') % self.env.user.name)
    
    def action_recalculate(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Solo se pueden recalcular liquidaciones en borrador.'))
            record.line_ids.unlink()
            record._create_liquidation_lines()
            record.message_post(body=_('Liquidación recalculada por %s') % self.env.user.name)
    
    def _create_liquidation_lines(self):
        self.ensure_one()
        if not self.id or not self.last_wage:
            return
            
        if self.line_ids:
            self.sudo().line_ids.unlink()
            
        lines = []
        sequence = 10
        
        if self.prestaciones_monto > 0:
            lines.append({
                'sequence': sequence,
                'description': 'Prestaciones Sociales',
                'days': self.work_period_years * 30,
                'amount': self.prestaciones_monto,
            })
            sequence += 10
        
        if self.vacaciones_monto > 0:
            lines.append({
                'sequence': sequence,
                'description': 'Vacaciones No Gozadas',
                'days': self.vacaciones_monto / self.salary_daily if self.salary_daily else 0,
                'amount': self.vacaciones_monto,
            })
            sequence += 10
        
        if self.bono_vacacional_monto > 0:
            lines.append({
                'sequence': sequence,
                'description': 'Bono Vacacional',
                'days': self.bono_vacacional_monto / self.salary_daily if self.salary_daily else 0,
                'amount': self.bono_vacacional_monto,
            })
            sequence += 10
        
        if self.preaviso_monto > 0:
            lines.append({
                'sequence': sequence,
                'description': 'Preaviso',
                'days': self.preaviso_monto / self.salary_daily if self.salary_daily else 0,
                'amount': self.preaviso_monto,
            })
            sequence += 10
        
        for line_vals in lines:
            line_vals['liquidation_id'] = self.id
            self.env['hr.liquidation.line'].create(line_vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.liquidation') or _('Nuevo')
        return super().create(vals_list)
    
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': _('Nuevo'),
            'state': 'draft',
            'created_by': self.env.user.id,
            'approved_by': False,
            'validated_date': False,
            'done_date': False,
        })
        return super().copy(default)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if not record.employee_id:
                record.contract_id = False
                record.date_start = False
                record.date_end = False
                record.last_wage = 0.0
                return

            # Buscar contrato activo
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'open'),
                ('company_id', '=', record.company_id.id)
            ], limit=1)

            if contract:
                record.contract_id = contract.id
                record.date_start = contract.date_start
                # Si el contrato tiene fecha de fin, usarla; si no, dejar vacío para que el usuario la ingrese
                record.date_end = contract.date_end or False
                record.last_wage = contract.wage
                record.currency_id = contract.company_id.currency_id.id
            else:
                record.contract_id = False
                record.date_start = False
                record.date_end = False
                record.last_wage = 0.0
                return {
                    'warning': {
                        'title': _('Advertencia'),
                        'message': _('El empleado seleccionado no tiene un contrato activo. Debe asignar uno o ingresar las fechas manualmente.')
                    }
                }

    @api.constrains('employee_id', 'contract_id')
    def _check_contract(self):
        for record in self:
            if not record.contract_id:
                # Permitir continuar solo si el usuario ingresa fechas manualmente
                if not (record.date_start and record.date_end):
                    raise ValidationError(_('Debe seleccionar un empleado con contrato activo o ingresar las fechas manualmente.'))


class HrLiquidationLine(models.Model):
    _name = 'hr.liquidation.line'
    _description = 'Línea de Liquidación'
    _order = 'sequence, id'
    
    liquidation_id = fields.Many2one('hr.liquidation', string='Liquidación', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Secuencia', default=10)
    description = fields.Char(string='Concepto', required=True)
    days = fields.Float(string='Días', digits=(16, 2))
    amount = fields.Monetary(string='Monto', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='liquidation_id.currency_id', store=True)
    
    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_('El monto no puede ser negativo.')) 