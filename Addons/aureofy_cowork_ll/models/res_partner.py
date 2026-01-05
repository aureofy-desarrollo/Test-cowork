# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cowork_member = fields.Boolean(string='Es Miembro Cowork', default=False)
    
    membership_ids = fields.One2many('cowork.membership', 'partner_id', string='Membresías')
    membership_count = fields.Integer(string='Nº Membresías', compute='_compute_membership_count')
    
    active_membership_id = fields.Many2one('cowork.membership', string='Membresía Activa',
                                            compute='_compute_active_membership')
    
    # Créditos
    total_credits = fields.Integer(string='Créditos Disponibles', compute='_compute_total_credits')
    credit_ids = fields.One2many('cowork.credits', 'partner_id', string='Historial de Créditos')
    
    # Información adicional para cowork
    cowork_notes = fields.Text(string='Notas de Cowork')
    preferred_space_type = fields.Selection([
        ('coworking', 'Coworking'),
        ('coliving', 'Coliving'),
    ], string='Tipo de Espacio Preferido')
    
    emergency_contact = fields.Char(string='Contacto de Emergencia')
    emergency_phone = fields.Char(string='Teléfono de Emergencia')
    
    @api.depends('membership_ids')
    def _compute_membership_count(self):
        for record in self:
            record.membership_count = len(record.membership_ids)
    
    @api.depends('membership_ids.state')
    def _compute_active_membership(self):
        for record in self:
            active = record.membership_ids.filtered(lambda m: m.state == 'active')
            record.active_membership_id = active[0] if active else False
    
    @api.depends('credit_ids.credits_amount')
    def _compute_total_credits(self):
        for record in self:
            record.total_credits = sum(record.credit_ids.mapped('credits_amount'))
    
    def action_view_memberships(self):
        """Ver membresías del contacto"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Membresías',
            'res_model': 'cowork.membership',
            'view_mode': 'tree,form,kanban',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
    
    def action_view_credits(self):
        """Ver historial de créditos"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Créditos',
            'res_model': 'cowork.credits',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
