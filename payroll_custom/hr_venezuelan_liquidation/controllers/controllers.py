# -*- coding: utf-8 -*-
# from odoo import http


# class Liquidation(http.Controller):
#     @http.route('/liquidation/liquidation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/liquidation/liquidation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('liquidation.listing', {
#             'root': '/liquidation/liquidation',
#             'objects': http.request.env['liquidation.liquidation'].search([]),
#         })

#     @http.route('/liquidation/liquidation/objects/<model("liquidation.liquidation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('liquidation.object', {
#             'object': obj
#         })

