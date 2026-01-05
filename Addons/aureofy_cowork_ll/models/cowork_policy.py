# -*- coding: utf-8 -*-

from odoo import models, fields


class CoworkPolicy(models.Model):
    _name = 'cowork.policy'
    _description = 'Política de Espacio'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    
    space_type = fields.Selection([
        ('coworking', 'Coworking'),
        ('coliving', 'Coliving'),
        ('both', 'Ambos'),
    ], string='Tipo de Espacio', default='both', required=True)
    
    description = fields.Html(string='Descripción', translate=True)
    
    is_mandatory = fields.Boolean(string='Obligatoria', default=True,
                                   help='El miembro debe aceptar esta política')
    
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
