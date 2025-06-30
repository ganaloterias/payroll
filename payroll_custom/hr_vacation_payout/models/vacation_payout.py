# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, time
import logging

_logger = logging.getLogger(__name__)

class HrVacationPayoutLine(models.Model):
    _name = 'hr.vacation.payout.line'
    _description = 'Línea de Pago de Vacaciones'
    _order = 'id desc'

    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'digits' or super()._valid_field_parameter(field, name)

    payout_id = fields.Many2one('hr.vacation.payout', required=True, ondelete='cascade')
    description = fields.Char(string='Descripción', required=True, default="Concepto", 
                            help="Descripción del concepto de pago de vacaciones")
    days = fields.Float(string='Días', digits=(16, 2), default=0.0)
    amount = fields.Monetary(string='Monto', required=True, default=0.0, 
                           digits=(16, 2))
    currency_id = fields.Many2one(related='payout_id.currency_id', store=True)

class HrVacationPayout(models.Model):
    _name = 'hr.vacation.payout'
    _description = 'Pago de Vacaciones'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc'

    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'digits' or super()._valid_field_parameter(field, name)

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=False, 
                      default=lambda self: _('Pago de Vacaciones'), tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, tracking=True)
    date = fields.Date(string='Fecha', required=True, default=fields.Date.context_today, tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato', compute='_compute_contract', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, 
                                 default=lambda self: self.env.company.currency_id.id)
    last_wage = fields.Monetary(string='Último Salario', currency_field='currency_id', required=True, 
                               tracking=True, default=0.0, digits=(16, 2))
    line_ids = fields.One2many('hr.vacation.payout.line', 'payout_id', string='Líneas de Pago')
    vacation_days = fields.Float(string='Días de Vacaciones', required=True, default=15.0, 
                               digits=(16, 2))
    vacation_bonus_days = fields.Float(string='Días de Bono Vacacional', compute='_compute_vacation_bonus', 
                                     store=True, digits=(16, 2))
    vacation_amount = fields.Monetary(string='Monto Vacaciones', currency_field='currency_id', 
                                     compute='_compute_amounts', store=True, digits=(16, 2))
    vacation_bonus_amount = fields.Monetary(string='Monto Bono Vacacional', currency_field='currency_id', 
                                           compute='_compute_amounts', store=True, digits=(16, 2))
    total_amount = fields.Monetary(string='Total a Pagar', currency_field='currency_id', 
                                  compute='_compute_amounts', store=True, digits=(16, 2))
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('done', 'Pagado'),
        ('rejected', 'Rechazado')
    ], string='Estado', default='draft', tracking=True)
    last_slip_id = fields.Many2one('hr.payslip', string='Última Nómina', readonly=True)
    calculation_details = fields.Text(string='Detalles del Cálculo', compute='_compute_calculation_details')
    work_years = fields.Float(string='Años de Servicio', compute='_compute_work_years', 
                            store=True, digits=(16, 1))
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    notes = fields.Text(string='Observaciones')
    related_payouts = fields.Many2many('hr.vacation.payout', compute='_compute_related_payouts', string='Pagos Relacionados')
    vacation_date_from = fields.Date(string='Fecha Inicio Vacaciones', tracking=True)
    vacation_date_to = fields.Date(string='Fecha Fin Vacaciones', tracking=True)
    leave_id = fields.Many2one('hr.leave', string='Ausencia', readonly=True, copy=False)
    create_leave = fields.Boolean(string='Crear Ausencia', default=True, 
                                help="Si está marcado, se creará automáticamente un registro de ausencia cuando se valide el pago")
    leave_state = fields.Selection(related='leave_id.state', string='Estado de la Ausencia', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') == _('Pago de Vacaciones'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.vacation.payout') or _('VP') + '/' + datetime.now().strftime('%Y/%m')
            
            # Si no hay empleado o fecha, establecer valores predeterminados
            if not vals.get('employee_id'):
                vals['employee_id'] = self.env['hr.employee'].search([], limit=1).id
                
            # Si se proporciona un empleado, calcular el salario automáticamente
            if vals.get('employee_id') and not vals.get('last_wage'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'open')
                ], limit=1)
                if contract:
                    vals['last_wage'] = contract.wage
                    
        records = super().create(vals_list)
        # Crear líneas después de que el registro principal existe
        for record in records:
            record._create_payment_lines()
        return records
        
    def write(self, vals):
        res = super().write(vals)
        # Si se modifican los campos relevantes, actualizar las líneas
        if any(field in vals for field in ['vacation_days', 'vacation_bonus_days', 'last_wage']):
            for record in self:
                record._create_payment_lines()
        return res
        
    def _create_payment_lines(self):
        """
        Crear o actualizar líneas de pago basadas en los montos calculados.
        
        Este método:
        1. Elimina las líneas existentes (si hay)
        2. Crea dos líneas nuevas:
           - Una para el monto de vacaciones
           - Una para el monto de bono vacacional
        
        Las líneas creadas corresponden exactamente a los montos calculados 
        en el método _compute_amounts, por lo que la suma de estas líneas
        siempre será igual al campo total_amount.
        """
        self.ensure_one()
        # Evitar crear líneas si el registro no tiene ID (nuevo) o faltan datos
        if not self.id or not self.vacation_days or not self.last_wage:
            return
            
        # Eliminar líneas existentes
        if self.line_ids:
            self.sudo().line_ids.unlink()
            
        # Definir las líneas a crear
        line_defs = [
            ('Días de Vacaciones', round(self.vacation_days, 0), self.vacation_amount),
            ('Bono Vacacional', round(self.vacation_bonus_days, 0), self.vacation_bonus_amount),
        ]
        
        # Crear las nuevas líneas
        for concept, days, amount in line_defs:
            self.env['hr.vacation.payout.line'].sudo().create({
                'payout_id': self.id,
                'description': concept,
                'days': max(0, days),
                'amount': round(max(0, amount), 2)
            })

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            rec.contract_id = contract.id if contract else False

    @api.depends('employee_id', 'date')
    def _compute_work_years(self):
        """Calcular años de servicio de forma más precisa"""
        for rec in self:
            if rec.employee_id and rec.contract_id and rec.date:
                # Calcular años de servicio desde el inicio del contrato hasta la fecha
                start_date = rec.contract_id.date_start
                end_date = rec.date
                
                if start_date and end_date and end_date >= start_date:
                    # Calcular diferencia en días
                    delta = end_date - start_date
                    days = delta.days
                    
                    # Convertir a años con precisión decimal
                    years = days / 365.25  # Usar 365.25 para considerar años bisiestos
                    rec.work_years = round(years, 1)
                else:
                    rec.work_years = 0.0
            else:
                rec.work_years = 0.0

    @api.depends('work_years')
    def _compute_vacation_bonus(self):
        """Calcular días de bono vacacional según LOTTT"""
        for rec in self:
            # Según LOTTT Venezuela, el bono vacacional es igual a los días de vacaciones
            rec.vacation_bonus_days = round(rec.vacation_days, 2)

    @api.depends('work_years', 'vacation_days')
    def _compute_vacation_days_according_law(self):
        """Calcular días de vacaciones según años de servicio (LOTTT)"""
        for rec in self:
            if rec.work_years >= 0:
                # Según LOTTT Venezuela:
                # - 15 días mínimo
                # - Aumenta 1 día por cada año de servicio hasta 30 días máximo
                base_days = 15
                additional_days = min(int(rec.work_years), 15)  # Máximo 15 días adicionales
                calculated_days = base_days + additional_days
                
                # Si no se han especificado días manualmente, usar el cálculo automático
                if not rec.vacation_days or rec.vacation_days == 15.0:  # Valor por defecto
                    rec.vacation_days = calculated_days

    @api.depends('vacation_days', 'vacation_bonus_days', 'last_wage')
    def _compute_amounts(self):
        """
        Calcula los montos a pagar basado en días de vacaciones, bono vacacional y salario.
        
        El total a pagar es la suma de:
        - Monto de vacaciones: días de vacaciones * salario diario
        - Monto de bono vacacional: días de bono vacacional * salario diario
        
        Las líneas de pago se crearán posteriormente en los métodos create y write.
        """
        for rec in self:
            if not (rec.vacation_days and rec.last_wage):
                rec.vacation_amount = 0.0
                rec.vacation_bonus_amount = 0.0
                rec.total_amount = 0.0
                continue
            
            # Factor diario según ley venezolana (LOTTT)
            daily_wage = round(rec.last_wage / 30.0, 2)
            
            rec.vacation_amount = round(rec.vacation_days * daily_wage, 2)
            rec.vacation_bonus_amount = round(rec.vacation_bonus_days * daily_wage, 2)
            rec.total_amount = round(rec.vacation_amount + rec.vacation_bonus_amount, 2)

    @api.depends('line_ids', 'work_years')
    def _compute_calculation_details(self):
        for rec in self:
            lines = [f"Años de servicio: {rec.work_years:.1f}"]
            for ln in rec.line_ids:
                lines.append(f"{ln.description}: {ln.days:.0f} días - {ln.amount:.2f}{rec.currency_id.symbol}")
            rec.calculation_details = "\n".join(lines)

    @api.onchange('employee_id', 'currency_id', 'date')
    def _onchange_last_slip(self):
        for rec in self:
            rec.last_slip_id = False
            rec.last_wage = 0.0
            
            if not (rec.employee_id and rec.currency_id and rec.date):
                continue
                
            payslips = self.env['hr.payslip'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'done'),
                ('date_to', '<=', rec.date)
            ], order='date_to desc', limit=1)
            
            if not payslips:
                return {'warning': {'title': _('Sin Nóminas'), 'message': _('No se encontraron nóminas procesadas para este empleado.')}}
            
            slip = payslips[0]
            rec.last_slip_id = slip.id
            
            # Obtener salario neto
            net_line = next((line for line in slip.line_ids if line.code == 'NET'), None)
            if net_line:
                rec.last_wage = net_line.total
            
            slip_currency = slip.company_id.currency_id
            if slip_currency.id != rec.currency_id.id:
                msg = _("""ATENCIÓN: La moneda de la nómina ({}) es diferente a la seleccionada ({}).
Se utilizará esta nómina por ser la más reciente, pero se recomienda verificar los montos calculados.""").format(
                    slip_currency.name,
                    rec.currency_id.name
                )
                return {'warning': {'title': _('Diferencia de Moneda'), 'message': msg}}

    @api.onchange('vacation_days', 'vacation_date_from')
    def _onchange_vacation_date_from(self):
        """Calcular la fecha fin en base a la fecha inicio y los días de vacaciones"""
        if self.vacation_date_from and self.vacation_days:
            # Calcular fecha fin sumando los días laborables (considerando solo L-V)
            date_from = self.vacation_date_from
            workdays = int(self.vacation_days)
            date_to = date_from
            
            # Añadir días laborables
            days_added = 0
            while days_added < workdays:
                date_to += timedelta(days=1)
                # Si no es fin de semana (0=lunes, 6=domingo en date.weekday())
                if date_to.weekday() < 5:  # L-V
                    days_added += 1
                    
            self.vacation_date_to = date_to
    
    @api.constrains('vacation_date_from', 'vacation_date_to')
    def _check_vacation_dates(self):
        """Validar que las fechas sean coherentes"""
        for record in self:
            if record.vacation_date_from and record.vacation_date_to:
                if record.vacation_date_from > record.vacation_date_to:
                    raise ValidationError(_("La fecha de inicio de vacaciones no puede ser posterior a la fecha de fin."))
                
                # Calcular días laborables entre las fechas
                day_count = 0
                current_date = record.vacation_date_from
                while current_date <= record.vacation_date_to:
                    if current_date.weekday() < 5:  # L-V
                        day_count += 1
                    current_date += timedelta(days=1)
                
                # Verificar si coinciden aproximadamente con los días pagados
                if abs(day_count - record.vacation_days) > 2:  # Tolerancia de 2 días
                    raise ValidationError(_(
                        "El número de días laborables entre las fechas ({}) difiere significativamente "
                        "de los días de vacaciones pagados ({}). Por favor, revise las fechas."
                    ).format(day_count, record.vacation_days))
    
    def action_validate(self):
        """Validar el pago de vacaciones"""
        self.ensure_one()
        
        # Validaciones adicionales podrían agregarse aquí
        
        # Cambiar estado
        self.write({'state': 'validated'})
        
        # Si está activada la creación de ausencias y no hay ya una creada
        if self.create_leave and not self.leave_id and self.vacation_date_from and self.vacation_date_to:
            self._create_leave_record()
            
        return True
        
    def action_done(self):
        """Marcar el pago de vacaciones como pagado"""
        self.ensure_one()
        
        if self.state != 'validated':
            raise UserError(_("Solo puede marcar como pagado un pago en estado 'Validado'."))
            
        # Cambiar estado a pagado
        self.write({'state': 'done'})
        
        # Aquí podrían crearse asientos contables u otras integraciones
        
        return True
        
    def action_draft(self):
        """Volver el pago a estado borrador para edición"""
        self.ensure_one()
        
        if self.state not in ['validated', 'rejected']:
            raise UserError(_("Solo puede volver a borrador un pago en estado 'Validado' o 'Rechazado'."))
            
        self.write({'state': 'draft'})
        return True
        
    def action_reject(self):
        """Rechazar el pago de vacaciones"""
        self.ensure_one()
        
        if self.state not in ['draft', 'validated']:
            raise UserError(_("Solo puede rechazar un pago en estado 'Borrador' o 'Validado'."))
            
        self.write({'state': 'rejected'})
        return True
        
    def action_view_employee(self):
        """Ver la ficha del empleado"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.depends('employee_id')
    def _compute_related_payouts(self):
        for rec in self:
            if rec.employee_id:
                rec.related_payouts = self.search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('id', '!=', rec.id)
                ])
            else:
                rec.related_payouts = False
                
    def action_fix_leave_codes(self):
        """
        Acción para corregir los tipos de ausencia
        que puedan estar generando problemas en nómina
        """
        self.ensure_one()
        if not self.leave_id:
            raise UserError(_("No hay ausencia asociada que corregir."))
            
        leave_type = self.leave_id.holiday_status_id
        
        # Verificar que el tipo de ausencia tenga el nombre correcto
        if 'vacación' not in leave_type.name.lower() and 'vacation' not in leave_type.name.lower():
            leave_type.sudo().write({'name': 'Vacaciones'})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nombre Corregido'),
                    'message': _('Se ha corregido el nombre del tipo de ausencia.'),
                    'sticky': False,
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Información'),
                    'message': _('El tipo de ausencia ya tiene el nombre correcto: %s') % leave_type.name,
                    'sticky': False,
                    'type': 'info',
                }
            }
            
    @api.model
    def fix_all_vacation_leave_types(self):
        """
        Método para ejecutar desde el shell o un cron job
        Corrige todos los tipos de ausencia relacionados con vacaciones
        que no tengan el nombre correcto.
        """
        # Buscar todos los tipos de ausencia que parezcan vacaciones
        leave_types = self.env['hr.leave.type'].search([
            '|', ('name', 'ilike', 'vaca'), ('name', 'ilike', 'vacation')
        ])
        
        count = 0
        for lt in leave_types:
            # Asegurar que tengan el nombre correcto
            if 'vacación' not in lt.name.lower() and 'vacation' not in lt.name.lower():
                lt.sudo().write({'name': 'Vacaciones'})
                count += 1
                
        _logger.info("Se han corregido %s tipos de ausencia para vacaciones.", count)
        return count

    def _create_leave_record(self):
        """Crear un registro de ausencia en hr.leave"""
        self.ensure_one()
        
        # Buscar un tipo de ausencia para vacaciones por nombre
        leave_type = self.env['hr.leave.type'].search([
            ('name', 'ilike', 'vacación'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        
        if not leave_type:
            # Si no encuentra por "vacación", buscar por "vacation"
            leave_type = self.env['hr.leave.type'].search([
                ('name', 'ilike', 'vacation'),
                '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
            ], limit=1)
        
        if not leave_type:
            # Si no encuentra ninguno, crear uno nuevo
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Vacaciones',
                'color': 3,  # Verde
                'time_type': 'leave',
                'request_unit': 'day',
                'requires_allocation': 'no',
                'employee_requests': 'yes',
                'leave_validation_type': 'hr',
                'allocation_validation_type': 'hr',
            })
            _logger.info("Tipo de ausencia para vacaciones creado automáticamente")
        
        # Crear el registro de ausencia
        leave_vals = {
            'holiday_status_id': leave_type.id,
            'employee_id': self.employee_id.id,
            'date_from': datetime.combine(self.vacation_date_from, time(8, 0, 0)),
            'date_to': datetime.combine(self.vacation_date_to, time(17, 0, 0)),
            'request_date_from': self.vacation_date_from,
            'request_date_to': self.vacation_date_to,
            'name': _('Vacaciones pagadas: %s') % self.name,
            'number_of_days': self.vacation_days,
        }
        
        leave = self.env['hr.leave'].create(leave_vals)
        
        # Intentar validar la ausencia automáticamente
        try:
            leave.action_validate()
        except Exception as e:
            _logger.warning("No se pudo validar automáticamente la ausencia: %s", str(e))
        
        # Guardar referencia al registro de ausencia
        self.leave_id = leave.id
        
    def action_cancel_leave(self):
        """Cancelar la ausencia asociada"""
        self.ensure_one()
        if self.leave_id and self.leave_id.state not in ['refuse', 'cancel']:
            try:
                self.leave_id.action_refuse()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Ausencia Cancelada'),
                        'message': _('La ausencia relacionada ha sido cancelada correctamente.'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('No se pudo cancelar la ausencia: %s') % str(e),
                        'sticky': False,
                        'type': 'danger',
                    }
                }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Advertencia'),
                'message': _('No hay ausencia para cancelar o ya está cancelada.'),
                'sticky': False,
                'type': 'warning',
            }
        }
        
    def action_view_leave(self):
        """Ver la ausencia asociada"""
        self.ensure_one()
        if not self.leave_id:
            raise UserError(_("No hay ausencia asociada a este pago de vacaciones."))
            
        return {
            'name': _('Ausencia'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'res_id': self.leave_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
        
    def action_view_leave_type(self):
        """Ver el tipo de ausencia asociado"""
        self.ensure_one()
        if not self.leave_id or not self.leave_id.holiday_status_id:
            raise UserError(_("No hay tipo de ausencia asociado."))
            
        leave_type = self.leave_id.holiday_status_id
        
        # Verificar que el tipo de ausencia tenga el nombre correcto
        if 'vacación' not in leave_type.name.lower() and 'vacation' not in leave_type.name.lower():
            msg = _("¡ADVERTENCIA! Este tipo de ausencia no tiene el nombre correcto para vacaciones.")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Tipo de Ausencia Incorrecto'),
                    'message': msg,
                    'sticky': True,
                    'type': 'warning',
                }
            }
        
        return {
            'name': _('Tipo de Ausencia'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.type',
            'res_id': leave_type.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('vacation_days')
    def _check_vacation_days_limits(self):
        """Validar límites de días de vacaciones según LOTTT"""
        for record in self:
            if record.vacation_days < 15:
                raise ValidationError(_("Los días de vacaciones no pueden ser menores a 15 según la LOTTT."))
            
            if record.vacation_days > 30:
                raise ValidationError(_("Los días de vacaciones no pueden exceder 30 según la LOTTT."))
            
            # Validar que coincida con años de servicio
            if record.work_years >= 0:
                expected_days = 15 + min(int(record.work_years), 15)
                if record.vacation_days > expected_days:
                    raise ValidationError(_(
                        "Los días de vacaciones (%s) exceden lo permitido para %s años de servicio (%s días)."
                    ) % (record.vacation_days, record.work_years, expected_days))

    @api.constrains('last_wage')
    def _check_last_wage(self):
        """Validar que el salario sea positivo"""
        for record in self:
            if record.last_wage <= 0:
                raise ValidationError(_("El salario debe ser mayor que cero."))

    @api.model
    def get_dashboard_stats(self):
        """Obtener estadísticas para el dashboard"""
        today = fields.Date.today()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        
        # Estadísticas generales
        total_payouts = self.search_count([])
        total_amount = sum(self.search([]).mapped('total_amount'))
        
        # Estadísticas por estado
        draft_count = self.search_count([('state', '=', 'draft')])
        validated_count = self.search_count([('state', '=', 'validated')])
        done_count = self.search_count([('state', '=', 'done')])
        rejected_count = self.search_count([('state', '=', 'rejected')])
        
        # Estadísticas del mes actual
        month_payouts = self.search_count([
            ('date', '>=', start_of_month),
            ('date', '<=', today)
        ])
        month_amount = sum(self.search([
            ('date', '>=', start_of_month),
            ('date', '<=', today)
        ]).mapped('total_amount'))
        
        # Estadísticas del año actual
        year_payouts = self.search_count([
            ('date', '>=', start_of_year),
            ('date', '<=', today)
        ])
        year_amount = sum(self.search([
            ('date', '>=', start_of_year),
            ('date', '<=', today)
        ]).mapped('total_amount'))
        
        # Top empleados por monto
        top_employees = self.read_group(
            [('state', '=', 'done')],
            ['employee_id', 'total_amount:sum'],
            ['employee_id'],
            limit=5,
            orderby='total_amount DESC'
        )
        
        return {
            'total_payouts': total_payouts,
            'total_amount': total_amount,
            'draft_count': draft_count,
            'validated_count': validated_count,
            'done_count': done_count,
            'rejected_count': rejected_count,
            'month_payouts': month_payouts,
            'month_amount': month_amount,
            'year_payouts': year_payouts,
            'year_amount': year_amount,
            'top_employees': top_employees,
        }
