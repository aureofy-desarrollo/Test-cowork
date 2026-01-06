# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """Otorgar créditos automáticamente al confirmar la orden"""
        res = super(SaleOrder, self)._action_confirm()
        
        for order in self:
            for line in order.order_line:
                # Buscar el producto de créditos usando referencia externa o configuración
                product_credits = self.env.ref('aureofy_cowork_ll.product_credits', raise_if_not_found=False)
                
                if product_credits and line.product_id == product_credits:
                    # Calcular cantidad de créditos
                    amount = int(line.product_uom_qty)
                    price_per_credit = line.price_unit
                    
                    if amount > 0:
                        self.env['cowork.credits'].create({
                            'partner_id': order.partner_id.id,
                            'credits_type': 'purchased',
                            'credits_amount': amount,
                            'price_per_credit': price_per_credit,
                            'sale_id': order.id,
                            'description': f'Compra de créditos (Orden {order.name})',
                        })
        
        return res
