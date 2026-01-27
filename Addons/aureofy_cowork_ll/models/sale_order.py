# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """Otorgar créditos automáticamente al confirmar la orden"""
        res = super(SaleOrder, self)._action_confirm()
        
        for order in self:
            for line in order.order_line:
                # 1. Buscar si el producto es un paquete de créditos específico
                package = self.env['cowork.credit.package'].search([('product_id', '=', line.product_id.id)], limit=1)
                
                if package:
                    # Usar configuración del paquete
                    amount = package.credits_amount * int(line.product_uom_qty)
                    validity_years = package.validity_years or 1
                    date_expiration = fields.Date.today() + relativedelta(years=validity_years)
                    
                    self.env['cowork.credits'].create({
                        'partner_id': order.partner_id.id,
                        'credits_type': 'purchased',
                        'credits_amount': amount,
                        'price_per_credit': package.price_per_credit,
                        'sale_id': order.id,
                        'sale_line_id': line.id,
                        'date_expiration': date_expiration,
                        'description': _('Compra de paquete: %s') % package.name,
                    })
                    continue

                # 2. Respaldo: Buscar el producto genérico de créditos
                product_credits = self.env.ref('aureofy_cowork_ll.product_credits', raise_if_not_found=False)
                
                if product_credits and line.product_id == product_credits:
                    amount = int(line.product_uom_qty)
                    if amount > 0:
                        # Regla por defecto: 1 año de validez
                        date_expiration = fields.Date.today() + relativedelta(years=1)
                        
                        self.env['cowork.credits'].create({
                            'partner_id': order.partner_id.id,
                            'credits_type': 'purchased',
                            'credits_amount': amount,
                            'price_per_credit': line.price_unit,
                            'sale_id': order.id,
                            'sale_line_id': line.id,
                            'date_expiration': date_expiration,
                            'description': _('Compra de créditos (Orden %s)') % order.name,
                        })
        
        return res
