# -*- coding: utf-8 -*-
# from odoo import http


# class HrLoanManagement(http.Controller):
#     @http.route('/hr_loan_management/hr_loan_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_loan_management/hr_loan_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_loan_management.listing', {
#             'root': '/hr_loan_management/hr_loan_management',
#             'objects': http.request.env['hr_loan_management.hr_loan_management'].search([]),
#         })

#     @http.route('/hr_loan_management/hr_loan_management/objects/<model("hr_loan_management.hr_loan_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_loan_management.object', {
#             'object': obj
#         })

