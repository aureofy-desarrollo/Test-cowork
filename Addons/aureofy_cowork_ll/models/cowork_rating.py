# -*- coding: utf-8 -*-

from odoo import models, fields


class CoworkRating(models.Model):
    _name = 'cowork.rating'
    _description = 'Valoración de Miembro'
    _order = 'date desc'

    membership_id = fields.Many2one('cowork.membership', string='Membresía',
                                     required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Miembro',
                                  related='membership_id.partner_id', store=True)
    
    rating = fields.Selection([
        ('1', '1 - Muy Malo'),
        ('2', '2 - Malo'),
        ('3', '3 - Regular'),
        ('4', '4 - Bueno'),
        ('5', '5 - Excelente'),
    ], string='Valoración', required=True)
    
    rating_value = fields.Integer(string='Valor', compute='_compute_rating_value', store=True)
    
    feedback = fields.Text(string='Comentarios')
    
    date = fields.Date(string='Fecha', default=fields.Date.today)
    
    space_type = fields.Selection(related='membership_id.space_type', store=True)
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    def _compute_rating_value(self):
        for record in self:
            record.rating_value = int(record.rating) if record.rating else 0
