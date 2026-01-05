# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CoworkMembershipPlan(models.Model):
    _name = 'cowork.membership.plan'
    _description = 'Plan de Membresía'
    _order = 'space_type, sequence, name'

    name = fields.Char(string='Nombre del Plan', required=True, translate=True)
    code = fields.Char(string='Código')
    sequence = fields.Integer(string='Secuencia', default=10)
    
    space_type = fields.Selection([
        ('coworking', 'Coworking'),
        ('coliving', 'Coliving'),
    ], string='Tipo de Espacio', required=True, default='coworking')
    
    duration_type = fields.Selection([
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('annual', 'Anual'),
    ], string='Tipo de Duración', required=True, default='monthly')
    
    duration_value = fields.Integer(string='Valor de Duración', default=1,
                                     help='Número de días/semanas/meses/años')
    
    price = fields.Monetary(string='Precio', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    # Sistema de Créditos
    credits_included = fields.Integer(string='Créditos Incluidos', default=0,
                                       help='Cantidad de créditos incluidos en este plan para usar en servicios adicionales')
    
    # Servicios incluidos
    included_service_ids = fields.Many2many('cowork.service', string='Servicios Incluidos',
                                             help='Servicios que están incluidos sin costo adicional')
    
    # Políticas aplicables
    policy_ids = fields.Many2many('cowork.policy', string='Políticas Aplicables')
    
    # Producto para facturación
    product_id = fields.Many2one('product.product', string='Producto para Facturación')
    
    description = fields.Html(string='Descripción', translate=True)
    features = fields.Html(string='Características', translate=True)
    
    # Configuración de renovación
    auto_renew = fields.Boolean(string='Renovación Automática', default=False)
    renewal_reminder_days = fields.Integer(string='Días para Recordatorio', default=7,
                                            help='Días antes del vencimiento para enviar recordatorio')
    
    # Depósito de seguridad
    requires_deposit = fields.Boolean(string='Requiere Depósito', default=False)
    deposit_amount = fields.Monetary(string='Monto del Depósito', currency_field='currency_id')
    
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    # Estadísticas
    membership_count = fields.Integer(string='Nº Membresías', compute='_compute_membership_count')
    
    @api.depends()
    def _compute_membership_count(self):
        for record in self:
            record.membership_count = self.env['cowork.membership'].search_count([
                ('plan_id', '=', record.id)
            ])
    
    def action_view_memberships(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Membresías',
            'res_model': 'cowork.membership',
            'view_mode': 'tree,form,kanban',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
    
    def _get_duration_days(self):
        """Calcular la duración en días"""
        self.ensure_one()
        if self.duration_type == 'daily':
            return self.duration_value
        elif self.duration_type == 'weekly':
            return self.duration_value * 7
        elif self.duration_type == 'monthly':
            return self.duration_value * 30
        elif self.duration_type == 'annual':
            return self.duration_value * 365
        return 0
