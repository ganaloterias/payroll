from odoo import fields, models

class HrContract(models.Model):
    _inherit = "hr.contract"
    
    schedule_pay = fields.Selection(
        selection_add=[
            ("quincenal", "Quincenal"),
        ],
        ondelete={"quincenal": "set default"}
    )
