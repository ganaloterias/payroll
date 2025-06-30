from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date

class HrEmployeeDependent(models.Model):
    _name = "hr.employee.dependent"
    _description = "Employee Dependent"
    _order = "name"

    name = fields.Char(
        string="Nombre del Hijo", 
        required=True,
        help="Nombre completo del hijo dependiente"
    )
    birth_date = fields.Date(
        string="Fecha de Nacimiento",
        help="Fecha de nacimiento del hijo dependiente"
    )
    relationship = fields.Selection([
        ('son', 'Hijo'),
        ('daughter', 'Hija'), 
        ('other', 'Otros')
    ], string="Relación", required=True, default='son')
    employee_id = fields.Many2one(
        "hr.employee", 
        string="Empleado", 
        ondelete="cascade", 
        required=True,
        help="Empleado al que pertenece este dependiente"
    )
    age = fields.Integer(
        string="Edad",
        compute="_compute_age",
        store=True,
        help="Edad calculada automáticamente"
    )
    is_minor = fields.Boolean(
        string="Es Menor de Edad",
        compute="_compute_age",
        store=True,
        help="Indica si el dependiente es menor de 18 años"
    )

    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for dependent in self:
            if dependent.birth_date:
                age = today.year - dependent.birth_date.year
                if today.month < dependent.birth_date.month or (
                    today.month == dependent.birth_date.month and 
                    today.day < dependent.birth_date.day
                ):
                    age -= 1
                dependent.age = age
                dependent.is_minor = age < 18
            else:
                dependent.age = 0
                dependent.is_minor = False

    @api.constrains('birth_date')
    def _check_birth_date(self):
        for record in self:
            if record.birth_date and record.birth_date > date.today():
                raise ValidationError(_("La fecha de nacimiento no puede ser futura."))

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if record.name and len(record.name.strip()) < 2:
                raise ValidationError(_("El nombre debe tener al menos 2 caracteres."))

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.employee_id.name})"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|',
                     ('name', operator, name),
                     ('employee_id.name', operator, name),
                     ('relationship', operator, name)]
        return self.search(domain + args, limit=limit).name_get()
    
    