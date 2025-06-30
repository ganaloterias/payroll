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

    dependent_children_count = fields.Integer(
        string="Número de Hijos",
        compute="_compute_dependent_children_count",
        store=True
    )

    @api.depends('dependent_children_ids')
    def _compute_dependent_children_count(self):
        for employee in self:
            employee.dependent_children_count = len(employee.dependent_children_ids)

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
