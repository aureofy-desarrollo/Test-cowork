# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CoworkService(models.Model):
    _name = 'cowork.service'
    _description = 'Servicio Adicional'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Código')
    sequence = fields.Integer(string='Secuencia', default=10)
    
    service_type = fields.Selection([
        ('meeting_room', 'Sala de Reuniones'),
        ('event_hall', 'Salón de Eventos'),
        ('shared_space', 'Espacio Compartido'),
        ('cafeteria', 'Cafetería'),
        ('locker', 'Taquilla'),
        ('parking', 'Estacionamiento'),
        ('internet', 'Internet Premium'),
        ('printing', 'Impresión'),
        ('phone_booth', 'Cabina Telefónica'),
        ('other', 'Otro'),
    ], string='Tipo de Servicio', required=True, default='other')
    
    space_type = fields.Selection([
        ('coworking', 'Coworking'),
        ('coliving', 'Coliving'),
        ('both', 'Ambos'),
    ], string='Aplica a', default='both')
    
    is_paid = fields.Boolean(string='Es de Pago', default=False)
    price = fields.Monetary(string='Precio', currency_field='currency_id')
    credits_cost = fields.Integer(string='Costo en Créditos', default=0,
                                   help='Cantidad de créditos necesarios para usar este servicio')
    allow_credit_payment = fields.Boolean(string='Permite Pago con Créditos', default=True,
                                           help='Si está activo, los miembros pueden pagar con créditos')
    
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    tag_ids = fields.Many2many('cowork.tag', string='Etiquetas')
    
    description = fields.Html(string='Descripción')
    access_rules = fields.Text(string='Reglas de Acceso')
    
    requires_approval = fields.Boolean(string='Requiere Aprobación', default=True)
    
    image = fields.Image(string='Imagen', max_width=512, max_height=512)
    
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    product_id = fields.Many2one('product.product', string='Producto',
                                  help='Producto para facturación')
    
    @api.onchange('is_paid')
    def _onchange_is_paid(self):
        if not self.is_paid:
            self.price = 0
            self.credits_cost = 0
