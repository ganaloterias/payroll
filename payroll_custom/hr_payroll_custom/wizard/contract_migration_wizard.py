from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ContractMigrationWizard(models.TransientModel):
    _name = 'contract.migration.wizard'
    _description = 'Asistente de Migración de Contratos a Multimoneda'

    contract_ids = fields.Many2many(
        'hr.contract',
        string='Contratos a Migrar',
        domain=[('state', '=', 'open')],
        help='Seleccione los contratos que desea migrar a soporte multimoneda'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda Principal',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='Moneda principal para la migración'
    )
    
    create_multiple_currencies = fields.Boolean(
        string='Crear Líneas para Múltiples Monedas',
        default=False,
        help='Si está marcado, creará líneas para todas las monedas configuradas'
    )
    
    additional_currencies = fields.Many2many(
        'res.currency',
        string='Monedas Adicionales',
        help='Monedas adicionales para crear líneas de salario'
    )
    
    contracts_count = fields.Integer(
        string='Número de Contratos',
        compute='_compute_contracts_info'
    )
    
    contracts_with_salary = fields.Integer(
        string='Contratos con Salario',
        compute='_compute_contracts_info'
    )
    
    contracts_without_salary = fields.Integer(
        string='Contratos sin Salario',
        compute='_compute_contracts_info'
    )
    
    migration_summary = fields.Text(
        string='Resumen de Migración',
        readonly=True
    )

    @api.depends('contract_ids')
    def _compute_contracts_info(self):
        for wizard in self:
            contracts = wizard.contract_ids
            wizard.contracts_count = len(contracts)
            wizard.contracts_with_salary = len(contracts.filtered(lambda c: c.wage and c.wage > 0))
            wizard.contracts_without_salary = len(contracts.filtered(lambda c: not c.wage or c.wage <= 0))

    @api.onchange('contract_ids')
    def _onchange_contracts(self):
        if self.contract_ids:
            contracts_with_multicurrency = self.contract_ids.filtered(
                lambda c: hasattr(c, 'salary_line_ids') and c.salary_line_ids
            )
            
            if contracts_with_multicurrency:
                return {
                    'warning': {
                        'title': _('Contratos con Soporte Multimoneda'),
                        'message': _(
                            'Los siguientes contratos ya tienen soporte multimoneda: %s'
                        ) % ', '.join(contracts_with_multicurrency.mapped('name'))
                    }
                }

    def action_analyze_contracts(self):
        self.ensure_one()
        
        if not self.contract_ids:
            raise UserError(_("Debe seleccionar al menos un contrato para analizar."))
        
        analysis_results = []
        
        for contract in self.contract_ids:
            has_multicurrency = hasattr(contract, 'salary_line_ids') and contract.salary_line_ids
            
            if has_multicurrency:
                analysis_results.append(f"✓ {contract.name}: Ya tiene soporte multimoneda")
            else:
                if contract.wage and contract.wage > 0:
                    analysis_results.append(f"→ {contract.name}: Salario {contract.wage} {contract.company_id.currency_id.name}")
                else:
                    analysis_results.append(f"⚠ {contract.name}: Sin salario configurado")
        
        self.migration_summary = "\n".join(analysis_results)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Análisis Completado'),
                'message': _('Se han analizado %s contratos. Revise el resumen.') % len(self.contract_ids),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_migrate_contracts(self):
        self.ensure_one()
        
        if not self.contract_ids:
            raise UserError(_("Debe seleccionar al menos un contrato para migrar."))
        
        migrated_count = 0
        errors = []
        
        for contract in self.contract_ids:
            try:
                if hasattr(contract, 'salary_line_ids') and contract.salary_line_ids:
                    continue  # Ya migrado
                
                if not contract.wage or contract.wage <= 0:
                    errors.append(f"{contract.name}: Sin salario configurado")
                    continue
                
                result = self._migrate_single_contract(contract)
                if result['success']:
                    migrated_count += 1
                else:
                    errors.append(f"{contract.name}: {result['error']}")
                    
            except Exception as e:
                _logger.error(f"Error migrando contrato {contract.name}: {str(e)}")
                errors.append(f"{contract.name}: {str(e)}")
        
        summary_lines = [f"Migración completada: {migrated_count} contratos migrados"]
        if errors:
            summary_lines.append("")
            summary_lines.append("Errores encontrados:")
            summary_lines.extend(errors)
        
        self.migration_summary = "\n".join(summary_lines)
        
        if migrated_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Migración Exitosa'),
                    'message': _('Se migraron %s contratos correctamente.') % migrated_count,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Migración Fallida'),
                    'message': _('No se pudo migrar ningún contrato. Revise los errores.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def _migrate_single_contract(self, contract):
        try:
            if not hasattr(self.env['hr.contract'], 'salary_line_ids'):
                return {'success': False, 'error': _("El módulo de contratos multimoneda no está disponible.")}
            
            if not self.env['ir.model'].search([('model', '=', 'hr.contract.salary.line')]):
                return {'success': False, 'error': _("El modelo de líneas de salario no está disponible.")}
            
            salary_line_vals = {
                'contract_id': contract.id,
                'currency_id': self.currency_id.id,
                'wage': contract.wage,
                'schedule_pay': contract.schedule_pay or 'monthly',
                'struct_id': contract.structure_type_id.default_struct_id.id if contract.structure_type_id else False,
                'date_start': contract.date_start or fields.Date.today(),
                'state': 'active',
                'company_id': contract.company_id.id,
                'notes': _("Migrado automáticamente desde contrato existente")
            }
            
            salary_line = self.env['hr.contract.salary.line'].create(salary_line_vals)
            
            if self.create_multiple_currencies and self.additional_currencies:
                for currency in self.additional_currencies:
                    if currency.id != self.currency_id.id:
                        try:
                            converted_wage = self.currency_id._convert(
                                contract.wage,
                                currency,
                                contract.company_id,
                                fields.Date.today()
                            )
                        except Exception:
                            converted_wage = contract.wage  # Fallback
                        
                        additional_line_vals = {
                            'contract_id': contract.id,
                            'currency_id': currency.id,
                            'wage': converted_wage,
                            'schedule_pay': contract.schedule_pay or 'monthly',
                            'struct_id': contract.structure_type_id.default_struct_id.id if contract.structure_type_id else False,
                            'date_start': contract.date_start or fields.Date.today(),
                            'state': 'active',
                            'company_id': contract.company_id.id,
                            'notes': _("Línea adicional creada durante migración")
                        }
                        
                        self.env['hr.contract.salary.line'].create(additional_line_vals)
            
            return {'success': True, 'salary_line_id': salary_line.id}
            
        except Exception as e:
            _logger.error(f"Error migrando contrato {contract.name}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def action_view_migrated_contracts(self):
        self.ensure_one()
        
        migrated_contracts = self.contract_ids.filtered(
            lambda c: hasattr(c, 'salary_line_ids') and c.salary_line_ids
        )
        
        if not migrated_contracts:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Contratos Migrados'),
                    'message': _('No hay contratos migrados para mostrar.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contratos Migrados'),
            'res_model': 'hr.contract',
            'view_mode': 'list,form',
            'domain': [('id', 'in', migrated_contracts.ids)],
            'context': {'default_employee_id': self.contract_ids[0].employee_id.id if self.contract_ids else False},
        }

    def action_view_salary_lines(self):
        self.ensure_one()
        
        salary_lines = self.env['hr.contract.salary.line'].search([
            ('contract_id', 'in', self.contract_ids.ids)
        ])
        
        if not salary_lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Líneas de Salario'),
                    'message': _('No hay líneas de salario para mostrar.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Líneas de Salario'),
            'res_model': 'hr.contract.salary.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', salary_lines.ids)],
        } 