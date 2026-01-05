# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    is_cowork_lead = fields.Boolean(string='Es Lead de Cowork', default=False)
    
    space_type = fields.Selection([
        ('coworking', 'Coworking'),
        ('coliving', 'Coliving'),
    ], string='Tipo de Espacio')
    
    preferred_desk_type = fields.Selection([
        ('flexible', 'Puesto Flexible'),
        ('private_cabin', 'Cabina Privada'),
        ('meeting_room', 'Sala de Reuniones'),
        ('hot_desk', 'Hot Desk'),
    ], string='Tipo de Escritorio Preferido')
    
    preferred_bed_type = fields.Selection([
        ('single', 'Individual'),
        ('shared', 'Compartida'),
        ('bunk', 'Litera'),
        ('private_room', 'Habitación Privada'),
    ], string='Tipo de Cama Preferida')
    
    preferred_start_date = fields.Date(string='Fecha de Inicio Preferida')
    city_preference = fields.Char(string='Ciudad Preferida')
    
    special_requirements = fields.Text(string='Requisitos Especiales')
    
    membership_id = fields.Many2one('cowork.membership', string='Membresía Creada',
                                     readonly=True)
    
    plan_id = fields.Many2one('cowork.membership.plan', string='Plan Interesado')
    
    def action_create_membership(self):
        """Crear membresía desde el lead"""
        self.ensure_one()
        
        # Crear o buscar partner
        if not self.partner_id:
            partner = self.env['res.partner'].create({
                'name': self.contact_name or self.name,
                'email': self.email_from,
                'phone': self.phone,
                'is_cowork_member': True,
            })
            self.partner_id = partner
        else:
            self.partner_id.is_cowork_member = True
        
        # Crear membresía
        membership_vals = {
            'partner_id': self.partner_id.id,
            'space_type': self.space_type,
            'date_start': self.preferred_start_date or fields.Date.today(),
            'requirements': self.special_requirements,
        }
        
        if self.plan_id:
            membership_vals['plan_id'] = self.plan_id.id
        
        membership = self.env['cowork.membership'].create(membership_vals)
        self.membership_id = membership
        
        # Marcar como ganado
        self.action_set_won()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Membresía',
            'res_model': 'cowork.membership',
            'res_id': membership.id,
            'view_mode': 'form',
        }
