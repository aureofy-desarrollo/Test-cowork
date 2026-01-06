# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CoworkPortal(CustomerPortal):

    @http.route(['/my/credits/buy'], type='http', auth="user", website=True)
    def portal_buy_credits(self, **kwargs):
        values = self._prepare_portal_layout_values()
        return request.render("aureofy_cowork_ll.portal_buy_credits", values)

    @http.route(['/my/credits/buy/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_buy_credits_submit(self, **kwargs):
        amount = int(kwargs.get('amount', 0))
        if amount <= 0:
            return request.redirect('/my/credits/buy')
            
        partner = request.env.user.partner_id
        product = request.env.ref('aureofy_cowork_ll.product_credits')
        
        # Create Sale Order
        so = request.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': amount,
            })]
        })
        
        # Redirect to the Sale Order for payment
        return request.redirect(so.get_portal_url())
