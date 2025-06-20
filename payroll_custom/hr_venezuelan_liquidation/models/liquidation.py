# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from .services.liquidation_calculator import LiquidationCalculator
from .services.payslip_finder import PayslipFinder
import logging

_logger = logging.getLogger(__name__)

class HrLiquidationLine(models.Model):
    _name = 'hr.liquidation.line'
    _description = 'Línea de Liquidación'
    _order = 'id desc'

    liquidation_id = fields.Many2one('hr.liquidation', required=True, ondelete='cascade')
    description = fields.Char(required=True, default="Concepto", 
                             help="Descripción del concepto de liquidación")
    days = fields.Float(digits=(16, 2), default=0.0)
    amount = fields.Monetary(required=True, default=0.0)
    currency_id = fields.Many2one(related='liquidation_id.currency_id', store=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('description'):
                vals['description'] = vals.get('description', 'Concepto') or 'Concepto'
        return super(HrLiquidationLine, self).create(vals_list)

class HrLiquidation(models.Model):
    _name = 'hr.liquidation'
    _description = 'Liquidación de Empleado'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _rec_name    = 'name'
    _order       = 'date_end desc'

    name                  = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _('Nueva'), tracking=True)
    employee_id           = fields.Many2one('hr.employee', required=True, tracking=True)
    liquidation_type      = fields.Selection([('resignation','Renuncia'),('dismissal','Despido')], string='Tipo de Liquidación', required=True)
    date_start            = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    date_end              = fields.Date(required=True, tracking=True)
    contract_start_date   = fields.Date(string='Fecha Inicio Contrato', compute='_compute_contract_dates', store=True)
    contract_end_date     = fields.Date(string='Fecha Fin Contrato',   compute='_compute_contract_dates', store=True)
    currency_id           = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id.id)
    last_wage             = fields.Monetary(currency_field='currency_id', required=True, tracking=True)
    line_ids              = fields.One2many('hr.liquidation.line','liquidation_id')
    prestaciones_monto    = fields.Monetary(compute='_compute_montos', store=True)
    vacaciones_monto      = fields.Monetary(compute='_compute_montos', store=True)
    bono_vacacional_monto = fields.Monetary(compute='_compute_montos', store=True)
    preaviso_monto        = fields.Monetary(compute='_compute_montos', store=True)
    total_liquidacion     = fields.Monetary(compute='_compute_montos', store=True)
    state                 = fields.Selection([('draft','Borrador'),('validated','Validado'),('done','Finalizado')], default='draft', tracking=True)
    last_slip_id          = fields.Many2one('hr.payslip', readonly=True)
    calculation_details   = fields.Text(compute='_compute_calculation_details')
    work_period_years     = fields.Float(compute='_compute_work_period', store=True)
    work_period_months    = fields.Integer(compute='_compute_work_period', store=True)
    created_by            = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    approved_by           = fields.Many2one('res.users', readonly=True)
    company_id            = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.liquidation') or _('Nueva')
        return super().create(vals_list)

    @api.depends('employee_id')
    def _compute_contract_dates(self):
        for rec in self:
            contract = self.env['hr.contract'].search([('employee_id','=',rec.employee_id.id),('state','=','open')], limit=1)
            rec.contract_start_date = contract.date_start if contract else False
            rec.contract_end_date   = contract.date_end if contract   else False

    @api.depends('date_start','date_end')
    def _compute_work_period(self):
        calc = LiquidationCalculator(self.env)
        for rec in self:
            if rec.date_start and rec.date_end:
                p = calc.calculate_work_period(rec.date_start, rec.date_end)
                rec.work_period_years  = p['years']
                rec.work_period_months = p['months']
            else:
                rec.work_period_years  = 0.0
                rec.work_period_months = 0

    @api.depends('date_start','date_end','last_wage')
    def _compute_montos(self):
        calc = LiquidationCalculator(self.env)
        for rec in self:
            rec.vacaciones_monto = 0.0
            rec.bono_vacacional_monto = 0.0
            rec.prestaciones_monto = 0.0
            rec.preaviso_monto = 0.0
            rec.total_liquidacion = 0.0
            
            if not (rec.date_start and rec.date_end and rec.last_wage):
                continue
            
            try:
                res = calc.calculate_all(rec.date_start, rec.date_end, rec.last_wage)
                
                rec.vacaciones_monto = res['vacation']['amount']
                rec.bono_vacacional_monto = res['vacation_bonus']['amount']
                rec.prestaciones_monto = res['social_benefits']['final_amount']
                rec.preaviso_monto = res['notice']['amount']
                rec.total_liquidacion = res['total']
                
                if rec.line_ids:
                    rec.sudo().line_ids.unlink()
                
                line_defs = [
                    ('Vacaciones', res['vacation']['days'], res['vacation']['amount']),
                    ('Bono Vacacional', res['vacation_bonus']['days'], res['vacation_bonus']['amount']),
                    ('Prestaciones Sociales', res['social_benefits']['method_c']['days'], res['social_benefits']['final_amount']),
                    ('Preaviso', res['notice']['days'], res['notice']['amount']),
                ]
                
                for concept, days, amount in line_defs:
                    if isinstance(concept, str) and concept and isinstance(days, (int, float)) and isinstance(amount, (int, float)):
                        try:
                            self.env['hr.liquidation.line'].sudo().create({
                                'liquidation_id': rec.id,
                                'description': concept,
                                'days': max(0, days),  
                                'amount': max(0, amount)
                            })
                        except Exception as e:
                            _logger.error(f"Error al crear línea '{concept}': {str(e)}")
            except Exception as e:
                _logger.error(f"Error en el cálculo de liquidación: {str(e)}")

    @api.depends('line_ids','work_period_years','work_period_months')
    def _compute_calculation_details(self):
        for rec in self:
            lines = [f"Período: {rec.work_period_years:.1f}años y {rec.work_period_months}meses"]
            for ln in rec.line_ids:
                lines.append(f"{ln.description}: {ln.days:.1f} días - {ln.amount:.2f}{rec.currency_id.symbol}")
            rec.calculation_details = "\n".join(lines)

    @api.onchange('employee_id','currency_id','date_end')
    def _onchange_last_slip(self):
        pf = PayslipFinder(self.env)
        for rec in self:
            rec.last_slip_id = False
            rec.last_wage = 0.0
            
            if not (rec.employee_id and rec.currency_id and rec.date_end):
                continue
                
            try:
                payslips = self.env['hr.payslip'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'done'),
                    ('date_to', '<=', rec.date_end)
                ], order='date_to desc')
                
                if not payslips:
                    return {'warning': {'title': _('Sin Nóminas'), 'message': _('No se encontraron nóminas procesadas para este empleado.')}}
                
                available_currencies = {}
                for ps in payslips[:5]: 
                    currency_name = ps.company_id.currency_id.name
                    if currency_name not in available_currencies:
                        available_currencies[currency_name] = []
                    available_currencies[currency_name].append({
                        'name': ps.name,
                        'date_from': ps.date_from,
                        'date_to': ps.date_to
                    })
                
                slip = pf.find_last_valid_payslip(
                    rec.employee_id.id, 
                    rec.date_start, 
                    rec.date_end, 
                    rec.currency_id.id
                )
                
                if slip:
                    rec.last_slip_id = slip.id
                    net_amount = pf.get_net_amount(slip)
                    if net_amount:
                        rec.last_wage = net_amount
                    
                    slip_currency = slip.company_id.currency_id
                    if slip_currency.id != rec.currency_id.id:
                        msg = _("""ATENCIÓN: La moneda de la nómina ({}) es diferente a la seleccionada ({}).
Se utilizará esta nómina por ser la más reciente, pero se recomienda verificar los montos calculados.

Nómina: {} del {} al {}
Monto: {:.2f} {}""").format(
                            slip_currency.name,
                            rec.currency_id.name,
                            slip.name, 
                            slip.date_from, 
                            slip.date_to, 
                            rec.last_wage, 
                            slip_currency.name
                        )
                        return {'warning': {'title': _('Diferencia de Moneda'), 'message': msg}}
                    else:
                        msg = _('Nómina encontrada: {} del {} al {} con monto {:.2f} {}').format(
                            slip.name, 
                            slip.date_from, 
                            slip.date_to, 
                            rec.last_wage, 
                            rec.currency_id.name
                        )
                        return {'warning': {'title': _('Información'), 'message': msg}}
                        
            except ValidationError as e:
                return {'warning': {'title': _('Sin Nómina'), 'message': str(e)}}
            except UserError as e:
                if available_currencies:
                    currencies_msg = ""
                    for curr, slips in available_currencies.items():
                        slip_info = ", ".join([s['name'] for s in slips])
                        currencies_msg += f"\n- {curr}: {slip_info}"
                    
                    msg = _("No se encontró ninguna nómina en la moneda '{}'. Monedas disponibles: {}").format(
                        rec.currency_id.name, currencies_msg
                    )
                    return {'warning': {'title': _('Información de Monedas'), 'message': msg}}
                return {'warning': {'title': _('Sin Nómina'), 'message': str(e)}}
            except Exception as e:
                return {'warning': {'title': _('Error'), 'message': f'Error al buscar nómina: {str(e)}'}}

    @api.constrains('employee_id')
    def _check_duplicate_liquidation(self):
        for rec in self:
            exists = self.search([
                ('employee_id','=',rec.employee_id.id),
                ('id','!=',rec.id),
                ('state','!=','cancelled')
            ], limit=1)
            if exists:
                raise ValidationError(_('Ya existe una liquidación activa para este empleado.'))

    @api.constrains('date_start','date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError(_('Fecha fin debe ser posterior a inicio.'))

    @api.constrains('date_end')
    def _check_not_future(self):
        from datetime import date
        for rec in self:
            if rec.date_end > date.today():
                raise ValidationError(_('La fecha de fin no puede ser futura.'))

    def action_validate(self):
        for rec in self:
            if rec.state=='draft':
                rec.write({'state':'validated','approved_by':self.env.user.id})
        return True

    def action_done(self):
        for rec in self:
            if rec.state=='validated':
                rec.state='done'
        return True
