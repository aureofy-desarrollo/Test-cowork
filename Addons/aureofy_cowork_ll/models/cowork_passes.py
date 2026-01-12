# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class CoworkPasses(models.Model):
    _name = 'cowork.passes'
    _description = 'Pases de Miembro'
    _order = 'date desc, id desc'

    partner_id = fields.Many2one('res.partner', string='Miembro', required=True,
                                  index=True, ondelete='cascade')
    membership_id = fields.Many2one('cowork.membership', string='Membresía',
                                     help='Membresía asociada si aplica')
    
    pass_type = fields.Selection([
        ('granted', 'Otorgados por Plan'),
        ('used', 'Usados'),
        ('refund', 'Reembolso'),
        ('bonus', 'Bonificación'),
        ('renewal', 'Renovación Mensual'),
        ('expired', 'Expirados'),
    ], string='Tipo', required=True)
    
    amount = fields.Integer(string='Cantidad de Pases', required=True,
                             help='Positivo para agregar, negativo para usar')
    
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    description = fields.Char(string='Descripción')
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)

    @api.model
    def get_partner_balance(self, partner_id):
        """Obtener balance de pases de un partner"""
        passes = self.search([('partner_id', '=', partner_id)])
        return sum(passes.mapped('amount')) or 0
