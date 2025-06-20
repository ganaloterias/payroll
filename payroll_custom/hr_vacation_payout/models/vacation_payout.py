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
        for rec in self:
            if rec.employee_id and rec.contract_id and rec.date:
                delta = rec.date - rec.contract_id.date_start
                rec.work_years = round(delta.days / 365.0, 1)  # Redondear a 1 decimal
            else:
                rec.work_years = 0.0

    @api.depends('work_years')
    def _compute_vacation_bonus(self):
        for rec in self:
            # Según LOTTT Venezuela, el bono vacacional es igual a los días de vacaciones
            rec.vacation_bonus_days = round(rec.vacation_days, 2)  # Redondear a 2 decimales

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
            
            daily_wage = round(rec.last_wage / 30.0, 2)  # Factor diario según ley venezolana, redondeado
            
            rec.vacation_amount = round(rec.vacation_days * daily_wage, 2)
            rec.vacation_bonus_amount = round(rec.vacation_bonus_days * daily_wage, 2)
            rec.total_amount = round(rec.vacation_amount + rec.vacation_bonus_amount, 2)
            
            # No crear líneas aquí para evitar errores en campos nulos
            # Las líneas se crearán en el método write y create

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
        Acción para corregir los códigos de tipos de ausencia
        que puedan estar generando problemas en nómina
        """
        self.ensure_one()
        if not self.leave_id:
            raise UserError(_("No hay ausencia asociada que corregir."))
            
        leave_type = self.leave_id.holiday_status_id
        
        if not leave_type.code:
            leave_type.sudo().write({'code': 'VACATION'})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Código Corregido'),
                    'message': _('Se ha asignado el código VACATION al tipo de ausencia.'),
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
                    'message': _('El tipo de ausencia ya tiene el código: %s') % leave_type.code,
                    'sticky': False,
                    'type': 'info',
                }
            }
            
    @api.model
    def fix_all_vacation_leave_types(self):
        """
        Método para ejecutar desde el shell o un cron job
        Corrige todos los tipos de ausencia relacionados con vacaciones
        que no tengan código.
        """
        # Buscar todos los tipos de ausencia que parezcan vacaciones y no tengan código
        leave_types = self.env['hr.leave.type'].search([
            '|', ('name', 'ilike', 'vaca'), ('name', 'ilike', 'vacation'),
            ('code', '=', False)
        ])
        
        count = 0
        for lt in leave_types:
            lt.sudo().write({'code': 'VACATION'})
            count += 1
            
        _logger.info("Se han corregido %s tipos de ausencia sin código.", count)
        return count

    def _create_leave_record(self):
        """Crear un registro de ausencia en hr.leave"""
        self.ensure_one()
        
        # Buscar un tipo de ausencia para vacaciones
        leave_type = self.env['hr.leave.type'].search([
            ('code', '=', 'VACATION'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        
        if not leave_type:
            leave_type = self.env['hr.leave.type'].search([
                ('name', 'ilike', 'vaca'),
                '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
            ], limit=1)
        
        if not leave_type:
            raise UserError(_("No se encontró un tipo de ausencia para vacaciones. Por favor, configure uno."))
        
        # Verificar si el tipo de ausencia tiene código, si no, se lo asignamos
        if not leave_type.code:
            _logger.warning("El tipo de ausencia para vacaciones no tiene código. Asignando código predeterminado 'VACATION'.")
            leave_type.sudo().write({'code': 'VACATION'})
        
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
        
        # Mostrar información sobre el código
        if not leave_type.code:
            msg = _("¡ADVERTENCIA! Este tipo de ausencia no tiene código asignado, lo que puede causar errores en nómina.")
            self.env.user.notify_warning(message=msg, title=_("Tipo de Ausencia Sin Código"), sticky=True)
        
        return {
            'name': _('Tipo de Ausencia'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.type',
            'res_id': leave_type.id,
            'view_mode': 'form',
            'target': 'current',
        }
