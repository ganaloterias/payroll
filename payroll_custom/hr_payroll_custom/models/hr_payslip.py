from odoo import models, _, api, fields
from datetime import datetime, time, timedelta
from pytz import timezone
import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    contract_warning_message = fields.Text(
        string="Advertencia de Contrato",
        readonly=True,
        help="Mensaje de advertencia relacionado con el contrato y moneda"
    )
    
    has_multicurrency_contract = fields.Boolean(
        string="Contrato Multimoneda",
        readonly=True,
        help="Indica si el contrato asociado tiene soporte multimoneda"
    )
    
    salary_line_id = fields.Many2one(
        'hr.contract.salary.line',
        string="Línea de Salario",
        readonly=True,
        help="Línea de salario específica del contrato multimoneda"
    )

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """Obtener líneas de días trabajados optimizado"""
        res = []
        
        valid_contracts = contracts.filtered(lambda c: c.resource_calendar_id)
        
        if not valid_contracts:
            return res
        
        valid_contracts.mapped('employee_id')
        valid_contracts.mapped('resource_calendar_id')
        
        for contract in valid_contracts:
            try:
                day_from = datetime.combine(date_from, time.min)
                day_to = datetime.combine(date_to, time.max)
                day_contract_start = datetime.combine(contract.date_start, time.min) if contract.date_start else day_from

                if day_from < day_contract_start:
                    day_from = day_contract_start

                contract_context = contract.with_context(
                    employee_id=contract.employee_id.id, 
                    exclude_public_holidays=True
                )

                rest_days_dict = self._compute_rest_days(contract, day_from, day_to)
                rest_days = rest_days_dict['number_of_days']
                
                work_days_dict = self._compute_worked_days(contract, day_from, day_to, rest_days)
                leaves = self._compute_leave_days(contract, day_from, day_to)
                night_bonus = self._compute_night_bonus(contract, day_from, day_to)
                special_days = self._compute_special_days(contract, day_from, day_to)
                overtime = self._compute_overtime(contract, day_from, day_to)
                mondays = self._compute_mondays(contract, day_from, day_to)

                res.extend(leaves)
                res.extend([work_days_dict, rest_days_dict, night_bonus, special_days, overtime, mondays])
                
            except Exception as e:
                _logger.error(f"Error procesando contrato {contract.name}: {str(e)}")
                continue

        return res

    def _compute_worked_days(self, contract, day_from, day_to, rest_days):
        try:
            work_data = contract.employee_id._get_work_days_data_batch(
                day_from, day_to, calendar=contract.resource_calendar_id, compute_leaves=False
            )

            if rest_days >= 5:
                max_days = 10
                max_hours = 75.0  
            else:
                max_days = 11
                max_hours = 82.5  

            employee_data = work_data.get(contract.employee_id.id, {})
            number_of_days = min(employee_data.get("days", 0), max_days)
            number_of_hours = min(employee_data.get("hours", 0), max_hours)

            return {
                "name": _("Dias habiles"),
                "sequence": 1,
                "code": "WORK100",
                "number_of_days": number_of_days,
                "number_of_hours": number_of_hours,
                "contract_id": contract.id,
            }
        except Exception as e:
            _logger.error(f"Error calculando días trabajados: {str(e)}")
            return {
                "name": _("Dias habiles"),
                "sequence": 1,
                "code": "WORK100",
                "number_of_days": 0.0,
                "number_of_hours": 0.0,
                "contract_id": contract.id,
            }

    def _compute_rest_days(self, contract, day_from, day_to):
        try:
            rest_days = sum(1 for i in range((day_to - day_from).days + 1) 
                          if (day_from + timedelta(days=i)).weekday() in [5, 6])

            return {
                "name": _("Descansos"),
                "sequence": 2,
                "code": "RESTDAYS",
                "number_of_days": rest_days,
                "number_of_hours": rest_days * 8,
                "contract_id": contract.id,
            }
        except Exception as e:
            _logger.error(f"Error calculando días de descanso: {str(e)}")
            return {
                "name": _("Descansos"),
                "sequence": 2,
                "code": "RESTDAYS",
                "number_of_days": 0.0,
                "number_of_hours": 0.0,
                "contract_id": contract.id,
            }

    def _compute_leave_days(self, contract, day_from, day_to):
        try:
            leaves_positive = (
                self.env["ir.config_parameter"].sudo().get_param("payroll.leaves_positive")
            )
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)

            leaves["GLOBAL"] = {
                "name": _("Ausencias Globales"),
                "sequence": 8,
                "code": "GLOBAL",
                "number_of_days": 0.0,
                "number_of_hours": 0.0,
                "contract_id": contract.id,
            }

            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id
            )

            for day, hours, leave in day_leave_intervals:
                holiday = leave[:1].holiday_id
                
                leave_code = self._get_leave_code(holiday)
                
                current_leave_struct = leaves.setdefault(
                    leave_code,
                    {
                        "name": holiday.holiday_status_id.name or _("Global Leaves"),
                        "sequence": 5,
                        "code": leave_code,
                        "number_of_days": 0.0,
                        "number_of_hours": 0.0,
                        "contract_id": contract.id,
                    },
                )

                if leaves_positive:
                    current_leave_struct["number_of_hours"] -= hours
                else:
                    current_leave_struct["number_of_hours"] += hours

                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )

                if work_hours:
                    if leaves_positive:
                        current_leave_struct["number_of_days"] -= hours / work_hours
                    else:
                        current_leave_struct["number_of_days"] += hours / work_hours

            return list(leaves.values())
            
        except Exception as e:
            _logger.error(f"Error calculando días de ausencia: {str(e)}")
            return [{
                "name": _("Ausencias Globales"),
                "sequence": 8,
                "code": "GLOBAL",
                "number_of_days": 0.0,
                "number_of_hours": 0.0,
                "contract_id": contract.id,
            }]

    def _get_leave_code(self, holiday):
        if not holiday.holiday_status_id:
            return "GLOBAL"
        
        if holiday.holiday_status_id.code:
            return holiday.holiday_status_id.code
        
        if 'vaca' in (holiday.holiday_status_id.name or '').lower():
            return "VACATION"
        
        leave_name = holiday.holiday_status_id.name or "LEAVE"
        leave_code = ''.join(word[0].upper() for word in leave_name.split()[:3])
        return leave_code if leave_code else "LEAVE"

    def _compute_night_bonus(self, contract, day_from, day_to):
        return {
            "name": _("Bono Nocturno"),
            "sequence": 3,
            "code": "NIGHT0",
            "number_of_days": 0.0,
            "number_of_hours": 0.0,
            "contract_id": contract.id,
        }

    def _compute_special_days(self, contract, day_from, day_to):
        return {
            "name": _("Dias Adicionales"),
            "sequence": 4,
            "code": "SPECIAL0",
            "number_of_days": 0.0,
            "number_of_hours": 0.0,
            "contract_id": contract.id,
        }

    def _compute_overtime(self, contract, day_from, day_to):
        return {
            "name": _("Horas Extra"),
            "sequence": 6,
            "code": "HE0",
            "number_of_days": 0.0,
            "number_of_hours": 0.0,
            "contract_id": contract.id,
        }

    def _compute_mondays(self, contract, day_from, day_to):
        try:
            monday_count = sum(1 for i in range((day_to - day_from).days + 1) 
                             if (day_from + timedelta(days=i)).weekday() == 0)

            return {
                "name": _("Lunes dentro del período"),
                "sequence": 7,
                "code": "MONDAY",
                "number_of_days": monday_count,
                "number_of_hours": monday_count * 8,
                "contract_id": contract.id,
            }
        except Exception as e:
            _logger.error(f"Error calculando lunes: {str(e)}")
            return {
                "name": _("Lunes dentro del período"),
                "sequence": 7,
                "code": "MONDAY",
                "number_of_days": 0.0,
                "number_of_hours": 0.0,
                "contract_id": contract.id,
            }

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        try:
            res = []
            current_structure = self.struct_id
            
            if current_structure:
                structure_ids = list(set(current_structure._get_parent_structure().ids))
            else:
                structure_ids = contracts.get_all_structures()
            
            rule_ids = (
                self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
            )
            sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
            
            payslip_inputs = (
                self.env["hr.salary.rule"].browse(sorted_rule_ids).mapped("input_ids")
            )
            
            for contract in contracts:
                for payslip_input in payslip_inputs:
                    res.append({
                        "name": payslip_input.name,
                        "code": payslip_input.code,
                        "contract_id": contract.id,
                    })
            
            return res
            
        except Exception as e:
            _logger.error(f"Error obteniendo inputs: {str(e)}")
            return []

    
    @api.onchange('employee_id', 'date_from', 'date_to', 'currency_id')
    def _onchange_contract_multicurrency(self):
        if self.employee_id and self.date_from and self.date_to:
            self._validate_and_set_contract()
    
    def _validate_and_set_contract(self):
        try:
            contract_handler = self.env['payroll.contract.handler']
            validation_result = contract_handler.validate_payslip_contract(self)
            
            if validation_result['success']:
                contract_info = validation_result['contract_info']
                
                self.has_multicurrency_contract = contract_info.get('has_multicurrency', False)
                self.salary_line_id = contract_info.get('salary_line_id', False)
                
                if contract_info.get('warning_message'):
                    self.contract_warning_message = contract_info['warning_message']
                else:
                    self.contract_warning_message = False
                    
            else:
                self.contract_warning_message = validation_result.get('warning_message', _("Error al validar el contrato"))
                self.has_multicurrency_contract = False
                self.salary_line_id = False
                
        except Exception as e:
            _logger.error(f"Error en validación de contrato multimoneda: {str(e)}")
            self.contract_warning_message = _("Error al validar el contrato: %s") % str(e)
    
    def action_validate_contract(self):
        self.ensure_one()
        self._validate_and_set_contract()
        
        if self.contract_warning_message:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Advertencia de Contrato'),
                    'message': self.contract_warning_message,
                    'type': 'warning',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Contrato Validado'),
                    'message': _('El contrato ha sido validado correctamente.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
    
    def action_view_contract_salary_lines(self):
        self.ensure_one()
        
        if not self.contract_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Contrato'),
                    'message': _('No hay contrato asociado a esta nómina.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        if hasattr(self.contract_id, 'action_view_salary_lines'):
            return self.contract_id.action_view_salary_lines()
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Funcionalidad No Disponible'),
                    'message': _('El contrato no tiene soporte multimoneda.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
    
    def compute_sheet(self):
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                payslip._validate_and_set_contract()
        
        return super().compute_sheet()
    
    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        
        for payslip in payslips:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                payslip._validate_and_set_contract()
        
        return payslips
