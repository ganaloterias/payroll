# -*- coding: utf-8 -*-
# from odoo import http


# class HrVacationPayout(http.Controller):
#     @http.route('/hr_vacation_payout/hr_vacation_payout', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_vacation_payout/hr_vacation_payout/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_vacation_payout.listing', {
#             'root': '/hr_vacation_payout/hr_vacation_payout',
#             'objects': http.request.env['hr_vacation_payout.hr_vacation_payout'].search([]),
#         })

#     @http.route('/hr_vacation_payout/hr_vacation_payout/objects/<model("hr_vacation_payout.hr_vacation_payout"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_vacation_payout.object', {
#             'object': obj
#         })

