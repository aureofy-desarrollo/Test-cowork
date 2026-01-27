# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class CoworkSellCreditPackage(models.TransientModel):
    _name = 'cowork.sell.credit.package'
    _description = 'Vender Paquete de Créditos'

    package_id = fields.Many2one('cowork.credit.package', string='Paquete', required=True)
    partner_id = fields.Many2one('res.partner', string='Miembro', required=True, 
                                  domain=[('is_cowork_member', '=', True)])
    
    amount = fields.Integer(string='Cantidad de Créditos', related='package_id.credits_amount', readonly=True)
    price = fields.Monetary(string='Precio', related='package_id.price', readonly=True)
    currency_id = fields.Many2one('res.currency', related='package_id.currency_id')

    def action_confirm(self):
        self.ensure_one()
        
        if not self.package_id.product_id:
            self.package_id._create_or_update_product()

        # Crear Orden de Venta
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'product_id': self.package_id.product_id.id,
                'name': _('Paquete de Créditos: %s') % self.package_id.name,
                'product_uom_qty': 1,
                'price_unit': self.package_id.price,
            })],
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Venta'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
