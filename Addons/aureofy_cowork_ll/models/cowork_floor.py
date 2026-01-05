# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CoworkFloor(models.Model):
    _name = 'cowork.floor'
    _description = 'Planta/Piso del Espacio'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    sequence = fields.Integer(string='Secuencia', default=10)
    building_name = fields.Char(string='Edificio')
    address = fields.Text(string='Dirección')
    city = fields.Char(string='Ciudad')
    
    desk_ids = fields.One2many('cowork.desk', 'floor_id', string='Escritorios')
    bed_ids = fields.One2many('cowork.bed', 'floor_id', string='Camas')
    
    desk_count = fields.Integer(string='Nº Escritorios', compute='_compute_counts')
    bed_count = fields.Integer(string='Nº Camas', compute='_compute_counts')
    
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía', 
                                  default=lambda self: self.env.company)
    
    @api.depends('desk_ids', 'bed_ids')
    def _compute_counts(self):
        for record in self:
            record.desk_count = len(record.desk_ids)
            record.bed_count = len(record.bed_ids)
    
    def action_view_desks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Escritorios',
            'res_model': 'cowork.desk',
            'view_mode': 'tree,form,kanban',
            'domain': [('floor_id', '=', self.id)],
            'context': {'default_floor_id': self.id},
        }
    
    def action_view_beds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Camas',
            'res_model': 'cowork.bed',
            'view_mode': 'tree,form,kanban',
            'domain': [('floor_id', '=', self.id)],
            'context': {'default_floor_id': self.id},
        }
