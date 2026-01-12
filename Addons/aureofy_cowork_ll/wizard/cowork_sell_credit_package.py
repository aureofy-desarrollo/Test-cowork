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
        # Llamar al método de compra de créditos
        self.env['cowork.credits'].purchase_credits(
            partner_id=self.partner_id.id,
            amount=self.package_id.credits_amount,
            price_per_credit=self.package_id.price_per_credit,
            validity_years=self.package_id.validity_years
        )
        return {'type': 'ir.actions.act_window_close'}
