# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MemberCardWizard(models.TransientModel):
    _name = 'cowork.member.card.wizard'
    _description = 'Asistente de Generación de Tarjetas de Miembro'

    membership_ids = fields.Many2many('cowork.membership', string='Membresías Seleccionadas')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            res['membership_ids'] = [(6, 0, active_ids)]
        return res
    
    def action_generate_cards(self):
        """Generar tarjetas de miembro en PDF"""
        self.ensure_one()
        
        return self.env.ref('aureofy_cowork_ll.action_report_member_card').report_action(
            self.membership_ids
        )
