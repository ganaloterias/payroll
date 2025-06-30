# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class LiquidationWizard(models.TransientModel):
    _name = 'hr.liquidation.wizard'
    _description = 'Asistente de Liquidación'

    employee_id = fields.Many2one(
        'hr.employee', 
        string='Empleado', 
        required=True,
        domain=[('active', '=', True)],
        help='Empleado para el cual se creará la liquidación'
    )
    date_end = fields.Date(
        string='Fecha Fin', 
        required=True, 
        default=fields.Date.context_today,
        help='Fecha de finalización del contrato'
    )
    liquidation_type = fields.Selection([
        ('resignation', 'Renuncia'),
        ('dismissal', 'Despido'),
        ('contract_end', 'Fin de Contrato'),
        ('mutual_agreement', 'Acuerdo Mutuo')
    ], string='Tipo de Liquidación', required=True)
    notes = fields.Text(
        string='Observaciones',
        help='Observaciones adicionales sobre la liquidación'
    )
    
    # Campos computados para información
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contrato',
        compute='_compute_contract_info',
        readonly=True
    )
    contract_start_date = fields.Date(
        string='Fecha Inicio Contrato',
        compute='_compute_contract_info',
        readonly=True
    )
    last_wage = fields.Monetary(
        string='Último Salario',
        compute='_compute_contract_info',
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        compute='_compute_contract_info',
        readonly=True
    )
    work_years = fields.Float(
        string='Años de Servicio',
        compute='_compute_contract_info',
        readonly=True,
        digits=(16, 1)
    )

    @api.depends('employee_id', 'date_end')
    def _compute_contract_info(self):
        """Calcular información del contrato y empleado"""
        for record in self:
            record.contract_id = False
            record.contract_start_date = False
            record.last_wage = 0.0
            record.currency_id = False
            record.work_years = 0.0
            
            if not record.employee_id or not record.date_end:
                continue
            
            # Buscar contrato activo
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'open'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if contract:
                record.contract_id = contract.id
                record.contract_start_date = contract.date_start
                record.last_wage = contract.wage
                record.currency_id = contract.company_id.currency_id.id
                
                # Calcular años de servicio
                if contract.date_start and record.date_end:
                    delta = record.date_end - contract.date_start
                    total_days = delta.days + 1
                    record.work_years = total_days / 365.25  # Usar 365.25 para años bisiestos

    @api.onchange('employee_id')
    def _onchange_employee(self):
        """Manejar cambios en el empleado"""
        if not self.employee_id:
            return
        
        # Verificar si ya existe una liquidación activa
        existing_liquidation = self.env['hr.liquidation'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['draft', 'validated'])
        ], limit=1)
        
        if existing_liquidation:
            return {
                'warning': {
                    'title': _('Liquidación Existente'),
                    'message': _(
                        'El empleado %s ya tiene una liquidación activa (%s). '
                        'Debe finalizar o cancelar la liquidación existente antes de crear una nueva.'
                    ) % (self.employee_id.name, existing_liquidation.name)
                }
            }
        
        # Verificar si tiene contrato activo
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open')
        ], limit=1)
        
        if not contract:
            return {
                'warning': {
                    'title': _('Sin Contrato Activo'),
                    'message': _('El empleado %s no tiene un contrato activo.') % self.employee_id.name
                }
            }

    @api.constrains('date_end')
    def _check_date_end(self):
        """Validar fecha de fin"""
        for record in self:
            if record.date_end > date.today():
                raise ValidationError(_('La fecha de fin no puede ser futura.'))
            
            if record.contract_start_date and record.date_end <= record.contract_start_date:
                raise ValidationError(_('La fecha de fin debe ser posterior a la fecha de inicio del contrato.'))

    def action_create_liquidation(self):
        """Crear liquidación desde el wizard"""
        self.ensure_one()
        
        # Validaciones adicionales
        if not self.employee_id:
            raise UserError(_('Debe seleccionar un empleado.'))
        
        if not self.date_end:
            raise UserError(_('Debe especificar la fecha de fin.'))
        
        if not self.liquidation_type:
            raise UserError(_('Debe especificar el tipo de liquidación.'))
        
        # Verificar contrato activo
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not contract:
            raise UserError(_('El empleado no tiene un contrato activo.'))
        
        # Verificar que no exista liquidación activa
        existing_liquidation = self.env['hr.liquidation'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['draft', 'validated'])
        ], limit=1)
        
        if existing_liquidation:
            raise UserError(_(
                'Ya existe una liquidación activa para el empleado %s. '
                'Debe finalizar o cancelar la liquidación existente antes de crear una nueva.'
            ) % self.employee_id.name)
        
        try:
            # Crear liquidación
            liquidation_vals = {
                'employee_id': self.employee_id.id,
                'liquidation_type': self.liquidation_type,
                'date_start': contract.date_start,
                'date_end': self.date_end,
                'currency_id': contract.company_id.currency_id.id,
                'last_wage': contract.wage,
                'notes': self.notes,
            }
            
            liquidation = self.env['hr.liquidation'].create(liquidation_vals)
            
            # Mensaje de confirmación
            liquidation.message_post(
                body=_('Liquidación creada desde asistente por %s') % self.env.user.name
            )
            
            _logger.info(f"Liquidación creada exitosamente: {liquidation.name} para empleado {self.employee_id.name}")
            
            # Retornar acción para mostrar la liquidación creada
            return {
                'name': _('Liquidación'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.liquidation',
                'res_id': liquidation.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {'default_employee_id': self.employee_id.id}
            }
            
        except Exception as e:
            _logger.error(f"Error al crear liquidación: {str(e)}")
            raise UserError(_('Error al crear la liquidación: %s') % str(e))
