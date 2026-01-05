# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CoworkBed(models.Model):
    _name = 'cowork.bed'
    _description = 'Cama de Coliving'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'floor_id, room_number, name'

    name = fields.Char(string='Nombre/Número', required=True, tracking=True)
    code = fields.Char(string='Código')
    
    bed_type = fields.Selection([
        ('single', 'Individual'),
        ('shared', 'Compartida'),
        ('bunk', 'Litera'),
        ('private_room', 'Habitación Privada'),
    ], string='Tipo de Cama', required=True, default='single', tracking=True)
    
    floor_id = fields.Many2one('cowork.floor', string='Planta', required=True,
                                ondelete='restrict')
    room_number = fields.Char(string='Número de Habitación')
    
    price_per_day = fields.Monetary(string='Precio por Día', currency_field='currency_id')
    price_per_month = fields.Monetary(string='Precio por Mes', currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    state = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Ocupada'),
        ('reserved', 'Reservada'),
        ('maintenance', 'Mantenimiento'),
    ], string='Estado', default='available', tracking=True)
    
    member_id = fields.Many2one('res.partner', string='Miembro Asignado',
                                 domain=[('is_cowork_member', '=', True)])
    membership_id = fields.Many2one('cowork.membership', string='Membresía Actual')
    
    amenity_ids = fields.Many2many('cowork.service', string='Comodidades Incluidas')
    tag_ids = fields.Many2many('cowork.tag', string='Etiquetas')
    
    image = fields.Image(string='Imagen', max_width=1024, max_height=1024)
    description = fields.Html(string='Descripción')
    
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    # Campos relacionados
    city = fields.Char(related='floor_id.city', string='Ciudad', store=True)
    
    def action_set_available(self):
        self.write({'state': 'available', 'member_id': False, 'membership_id': False})
    
    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})
    
    @api.model
    def get_available_by_type(self, bed_type, city=None):
        """Obtener camas disponibles filtradas por tipo y ciudad"""
        domain = [('state', '=', 'available'), ('bed_type', '=', bed_type)]
        if city:
            domain.append(('city', 'ilike', city))
        return self.search(domain)
