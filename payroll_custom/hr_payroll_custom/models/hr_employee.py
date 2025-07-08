from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    dependent_children_ids = fields.One2many(
        "hr.employee.dependent", 
        "employee_id", 
        string="Hijos Dependientes",
        help="Hijos dependientes del empleado"
    )

    def action_add_child(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Añadir Hijo Dependiente'),
            'res_model': 'hr.employee.dependent',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_relationship': 'son'
            },
        }

    def action_view_dependents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Hijos Dependientes'),
            'res_model': 'hr.employee.dependent',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
