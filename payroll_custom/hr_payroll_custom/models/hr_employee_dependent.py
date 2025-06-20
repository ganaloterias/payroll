# -*- coding: utf-8 -*-
from odoo import fields, models

class HrEmployeeDependent(models.Model):
    _name = "hr.employee.dependent"
    _description = "Employee Dependent"

    name = fields.Char(string="Nombre del Hijo", required=True)
    birth_date = fields.Date(string="Fecha de Nacimiento")
    relationship = fields.Selection([('son', 'Hijo'),('daughter', 'Hija'),('other', 'Otros'),], string="Relación", required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", ondelete="cascade", required=True) 
    
    