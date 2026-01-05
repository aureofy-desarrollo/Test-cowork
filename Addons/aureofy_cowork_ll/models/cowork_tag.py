# -*- coding: utf-8 -*-

from odoo import models, fields


class CoworkTag(models.Model):
    _name = 'cowork.tag'
    _description = 'Etiqueta'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    color = fields.Integer(string='Color', default=0)
    
    active = fields.Boolean(string='Activo', default=True)
