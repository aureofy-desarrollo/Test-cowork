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
    
    # Configuración de renovación y recurrencia
    is_recurring = fields.Boolean(string='Es Recurrente', default=False,
                                   help='Si es verdadero, la membresía se renueva automáticamente y otorga créditos/pases mensualmente.')
    
    passes_included = fields.Integer(string='Pases Incluidos (Mes)', default=0,
                                      help='Cantidad de pases de acceso diario incluidos por mes.')
    
    call_room_hours_included = fields.Integer(string='Horas de Call Room Incluidas (Mes)', default=0,
                                               help='Horas de uso de cabinas telefónicas incluidas por mes.')

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
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._create_or_update_product()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['name', 'price', 'product_id', 'currency_id']):
            for record in self:
                record._create_or_update_product()
        return res

    def _create_or_update_product(self):
        """Crear o actualizar producto relacionado"""
        self.ensure_one()
        if not self.product_id:
            # Crear producto si no existe
            product = self.env['product.product'].create({
                'name': self.name,
                'type': 'service',
                'list_price': self.price,
                'currency_id': self.currency_id.id,
                'detailed_type': 'service',
                'taxes_id': False,  # Opcional: configurar impuestos por defecto
            })
            self.product_id = product.id
        else:
            # Actualizar producto existente
            self.product_id.write({
                'name': self.name,
                'list_price': self.price,
                'currency_id': self.currency_id.id,
            })
    
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

