# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    dependent_children_ids = fields.One2many(
        "hr.employee.dependent", "employee_id", string="Hijos Dependientes"
    )

    def action_add_child(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Añadir Hijo Dependiente',
            'res_model': 'hr.employee.dependent',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
