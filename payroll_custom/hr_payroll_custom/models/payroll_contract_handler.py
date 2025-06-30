from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class PayrollContractHandler(models.Model):
    _name = 'payroll.contract.handler'
    _description = 'Manejador de Contratos para Nómina'
    
    @api.model
    def get_contract_for_payslip(self, employee_id, date_from, date_to, currency_id=None):
        try:
            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id),
                ('state', '=', 'open'),
                ('date_start', '<=', date_to),
                '|', ('date_end', '=', False), ('date_end', '>=', date_from)
            ])
            if not contracts:
                return {
                    'contract_id': False,
                    'wage': 0.0,
                    'currency_id': currency_id,
                    'has_multicurrency': False,
                    'warning_message': _("No se encontró contrato válido para el empleado en el período especificado.")
                }
            contract = contracts.sorted('date_start', reverse=True)[0]
            if not currency_id:
                currency_id = self.env.company.currency_id.id
            has_multicurrency = hasattr(contract, 'salary_line_ids') and contract.salary_line_ids
            if has_multicurrency:
                return self._get_multicurrency_contract_info(contract, currency_id, date_from, date_to)
            else:
                return self._get_standard_contract_info(contract, currency_id)
        except Exception as e:
            _logger.error(f"Error obteniendo contrato para nómina: {str(e)}")
            return {
                'contract_id': False,
                'wage': 0.0,
                'currency_id': currency_id,
                'has_multicurrency': False,
                'warning_message': _("Error al obtener información del contrato: %s") % str(e)
            }
    def _get_multicurrency_contract_info(self, contract, currency_id, date_from, date_to):
        try:
            if not hasattr(contract, 'get_salary_for_payslip'):
                return self._get_standard_contract_info(contract, currency_id)
            salary_info = contract.get_salary_for_payslip(contract.id, currency_id, date_from, date_to)
            if salary_info.get('wage', 0) > 0:
                return {
                    'contract_id': contract.id,
                    'wage': salary_info['wage'],
                    'currency_id': currency_id,
                    'schedule_pay': salary_info.get('schedule_pay', 'monthly'),
                    'struct_id': salary_info.get('struct_id'),
                    'has_multicurrency': True,
                    'salary_line_id': salary_info.get('salary_line_id'),
                    'warning_message': False
                }
            else:
                return {
                    'contract_id': contract.id,
                    'wage': 0.0,
                    'currency_id': currency_id,
                    'has_multicurrency': True,
                    'warning_message': _(
                        "No se encontró salario configurado para la moneda %s en el período especificado. "
                        "Verifique las líneas de salario del contrato."
                    ) % self.env['res.currency'].browse(currency_id).name
                }
        except Exception as e:
            _logger.error(f"Error obteniendo contrato multimoneda: {str(e)}")
            return {
                'contract_id': contract.id,
                'wage': 0.0,
                'currency_id': currency_id,
                'has_multicurrency': True,
                'warning_message': _("Error al obtener salario multimoneda: %s") % str(e)
            }
    def _get_standard_contract_info(self, contract, currency_id):
        try:
            contract_currency_id = contract.company_id.currency_id.id
            if currency_id != contract_currency_id:
                return {
                    'contract_id': contract.id,
                    'wage': contract.wage or 0.0,
                    'currency_id': contract_currency_id,
                    'schedule_pay': contract.schedule_pay or 'monthly',
                    'struct_id': contract.structure_type_id.default_struct_id.id if contract.structure_type_id else False,
                    'has_multicurrency': False,
                    'warning_message': _(
                        "El contrato usa la moneda %s pero la nómina está configurada para %s. "
                        "Considere migrar el contrato a soporte multimoneda."
                    ) % (
                        contract.company_id.currency_id.name,
                        self.env['res.currency'].browse(currency_id).name
                    )
                }
            else:
                return {
                    'contract_id': contract.id,
                    'wage': contract.wage or 0.0,
                    'currency_id': contract_currency_id,
                    'schedule_pay': contract.schedule_pay or 'monthly',
                    'struct_id': contract.structure_type_id.default_struct_id.id if contract.structure_type_id else False,
                    'has_multicurrency': False,
                    'warning_message': False
                }
        except Exception as e:
            _logger.error(f"Error obteniendo contrato estándar: {str(e)}")
            return {
                'contract_id': contract.id,
                'wage': 0.0,
                'currency_id': currency_id,
                'has_multicurrency': False,
                'warning_message': _("Error al obtener información del contrato estándar: %s") % str(e)
            }
    @api.model
    def validate_payslip_contract(self, payslip):
        try:
            if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
                return {
                    'success': False,
                    'warning_message': _("Faltan datos requeridos para validar el contrato.")
                }
            contract_info = self.get_contract_for_payslip(
                payslip.employee_id.id,
                payslip.date_from,
                payslip.date_to,
                payslip.currency_id.id if payslip.currency_id else None
            )
            if not contract_info.get('contract_id'):
                return {
                    'success': False,
                    'warning_message': contract_info.get('warning_message', _("No se pudo obtener información del contrato."))
                }
            if payslip.contract_id.id != contract_info['contract_id']:
                payslip.contract_id = contract_info['contract_id']
            if contract_info.get('struct_id') and payslip.struct_id.id != contract_info['struct_id']:
                payslip.struct_id = contract_info['struct_id']
            return {
                'success': True,
                'contract_info': contract_info,
                'warning_message': contract_info.get('warning_message'),
                'has_multicurrency': contract_info.get('has_multicurrency', False)
            }
        except Exception as e:
            _logger.error(f"Error validando contrato de nómina: {str(e)}")
            return {
                'success': False,
                'warning_message': _("Error al validar el contrato: %s") % str(e)
            }
    @api.model
    def get_contract_warnings(self, employee_id, date_from, date_to, currency_id=None):
        warnings = []
        try:
            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', employee_id),
                ('state', '=', 'open')
            ])
            for contract in contracts:
                if hasattr(contract, 'salary_line_ids') and contract.salary_line_ids:
                    if currency_id:
                        active_lines = contract.salary_line_ids.filtered(
                            lambda line: line.currency_id.id == currency_id and line.state == 'active'
                        )
                        if not active_lines:
                            warnings.append(_(
                                "El contrato %s tiene soporte multimoneda pero no hay líneas activas para la moneda %s"
                            ) % (contract.name, self.env['res.currency'].browse(currency_id).name))
                else:
                    if currency_id and contract.company_id.currency_id.id != currency_id:
                        warnings.append(_(
                            "El contrato %s no tiene soporte multimoneda y usa una moneda diferente"
                        ) % contract.name)
        except Exception as e:
            _logger.error(f"Error obteniendo advertencias de contratos: {str(e)}")
            warnings.append(_("Error al verificar contratos: %s") % str(e))
        return warnings 