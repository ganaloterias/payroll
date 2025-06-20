from odoo import models, _, api
from datetime import datetime, time, timedelta
from pytz import timezone

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = []
        for contract in contracts.filtered(lambda c: c.resource_calendar_id):
            if not contract:
                continue

            day_from = datetime.combine(date_from, time.min)
            day_to = datetime.combine(date_to, time.max)
            day_contract_start = datetime.combine(contract.date_start, time.min) if contract.date_start else day_from

            if contract:
                contract = contract.with_context(employee_id=self.employee_id.id, exclude_public_holidays=True)

            if day_from < day_contract_start:
                day_from = day_contract_start

            rest_days_dict = self._compute_rest_days(contract, day_from, day_to)
            rest_days = rest_days_dict['number_of_days']
            work_days_dict = self._compute_worked_days(contract, day_from, day_to, rest_days)
            leaves = self._compute_leave_days(contract, day_from, day_to)
            night_bonus = self._compute_night_bonus(contract, day_from, day_to)
            special_days = self._compute_special_days(contract, day_from, day_to)
            overtime = self._compute_overtime(contract, day_from, day_to)
            mondays = self._compute_mondays(contract, day_from, day_to)

            res.extend(leaves)
            res.append(work_days_dict)
            res.append(rest_days_dict)
            res.append(night_bonus)
            res.append(special_days)
            res.append(overtime)
            res.append(mondays)

        return res

    def _compute_worked_days(self, contract, day_from, day_to, rest_days):
        work_data = contract.employee_id._get_work_days_data_batch(
            day_from, day_to, calendar=contract.resource_calendar_id, compute_leaves=False
        )

        if rest_days >= 5:
            max_days = 10
            max_hours = 75.0  
        else:
            max_days = 11
            max_hours = 82.5  

        number_of_days = min(work_data[contract.employee_id.id]["days"], max_days)
        number_of_hours = min(work_data[contract.employee_id.id]["hours"], max_hours)

        return {
            "name": _("Dias habiles"),
            "sequence": 1,
            "code": "WORK100",
            "number_of_days": number_of_days,
            "number_of_hours": number_of_hours,
            "contract_id": contract.id,
        }

    def _compute_rest_days(self, contract, day_from, day_to):
        rest_days = 0.0
        current_date = day_from

        while current_date <= day_to:
            if current_date.weekday() in [5, 6]:
                rest_days += 1
            current_date += timedelta(days=1)

        return {
            "name": _("Descansos"),
            "sequence": 2,
            "code": "RESTDAYS",
            "number_of_days": rest_days,
            "number_of_hours": rest_days * 8,  
            "contract_id": contract.id,
        }

    def _compute_leave_days(self, contract, day_from, day_to):
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
            if holiday.holiday_status_id:
                if not holiday.holiday_status_id.code:
                    if 'vaca' in (holiday.holiday_status_id.name or '').lower():
                        leave_code = "VACATION"
                    else:
                        leave_name = holiday.holiday_status_id.name or "LEAVE"
                        leave_code = ''.join(word[0].upper() for word in leave_name.split()[:3])
                        if not leave_code:
                            leave_code = "LEAVE"
                else:
                    leave_code = holiday.holiday_status_id.code
            else:
                leave_code = "GLOBAL"

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
        monday_count = 0
        current_date = day_from

        while current_date <= day_to:
            if current_date.weekday() == 0: 
                monday_count += 1
            current_date += timedelta(days=1)

        return {
            "name": _("Lunes dentro del período"),
            "sequence": 7,
            "code": "MONDAY",
            "number_of_days": monday_count,
            "number_of_hours": monday_count * 8,
            "contract_id": contract.id,
        }

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []
        current_structure = self.struct_id
        structure_ids = contracts.get_all_structures()
        if current_structure:
            structure_ids = list(set(current_structure._get_parent_structure().ids))
        rule_ids = (
            self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
        )
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        payslip_inputs = (
            self.env["hr.salary.rule"].browse(sorted_rule_ids).mapped("input_ids")
        )
        for contract in contracts:
            for payslip_input in payslip_inputs:
                res.append(
                    {
                        "name": payslip_input.name,
                        "code": payslip_input.code,
                        "contract_id": contract.id,
                    }
                )
        return res
