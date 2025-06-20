# -*- coding: utf-8 -*-
# from odoo import http


# class HrPayrollCustom(http.Controller):
#     @http.route('/hr_payroll_custom/hr_payroll_custom', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_payroll_custom/hr_payroll_custom/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_payroll_custom.listing', {
#             'root': '/hr_payroll_custom/hr_payroll_custom',
#             'objects': http.request.env['hr_payroll_custom.hr_payroll_custom'].search([]),
#         })

#     @http.route('/hr_payroll_custom/hr_payroll_custom/objects/<model("hr_payroll_custom.hr_payroll_custom"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_payroll_custom.object', {
#             'object': obj
#         })

