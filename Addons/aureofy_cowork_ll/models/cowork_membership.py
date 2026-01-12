# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class CoworkMembership(models.Model):
    _name = 'cowork.membership'
    _description = 'Membresía'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'name desc'

    name = fields.Char(string='Número de Membresía', readonly=True, copy=False,
                       default=lambda self: _('Nuevo'))
    
    partner_id = fields.Many2one('res.partner', string='Miembro', required=True,
                                  tracking=True, index=True)
    partner_email = fields.Char(related='partner_id.email', string='Email')
    partner_phone = fields.Char(related='partner_id.phone', string='Teléfono')
    partner_image = fields.Image(related='partner_id.image_128', string='Foto')
    
    plan_id = fields.Many2one('cowork.membership.plan', string='Plan de Membresía',
                               required=True, tracking=True)
    
    space_type = fields.Selection(string='Tipo de Espacio', related='plan_id.space_type', store=True)
    
    # Asignación de espacio
    desk_id = fields.Many2one('cowork.desk', string='Escritorio Asignado',
                               domain=[('state', '=', 'available')])
    bed_id = fields.Many2one('cowork.bed', string='Cama Asignada',
                              domain=[('state', '=', 'available')])
    floor_id = fields.Many2one('cowork.floor', string='Piso Exclusivo',
                                domain=[('is_exclusive', '=', True), ('state', '=', 'available')])
    
    # Fechas
    date_start = fields.Date(string='Fecha de Inicio', required=True, tracking=True)
    date_end = fields.Date(string='Fecha de Fin', compute='_compute_date_end', 
                           store=True, tracking=True)
    
    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('active', 'Activa'),
        ('expired', 'Expirada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft', tracking=True, index=True)
    
    # Créditos
    credits_granted = fields.Integer(string='Créditos Otorgados', 
                                      compute='_compute_credits', store=True)
    credits_used = fields.Integer(string='Créditos Usados', compute='_compute_credits_used',
                                   store=True)
    credits_remaining = fields.Integer(string='Créditos Disponibles', 
                                        compute='_compute_credits_remaining')
    
    # Servicios y accesos
    service_ids = fields.Many2many('cowork.service', string='Servicios Adicionales')
    access_request_ids = fields.One2many('cowork.access.request', 'membership_id',
                                          string='Solicitudes de Acceso')
    access_request_count = fields.Integer(compute='_compute_access_request_count')
    
    # Políticas
    policy_ids = fields.Many2many('cowork.policy', string='Políticas Acordadas')
    policies_accepted = fields.Boolean(string='Políticas Aceptadas', default=False)

    # Pases y Horas
    passes_granted = fields.Integer(string='Pases Otorgados (Mes)', 
                                     compute='_compute_passes', store=True)
    passes_used = fields.Integer(string='Pases Usados (Mes)', default=0)
    passes_remaining = fields.Integer(string='Pases Disponibles', 
                                       compute='_compute_passes_remaining')
    
    call_room_hours_granted = fields.Integer(string='Horas Call Room (Mes)',
                                              compute='_compute_call_room_hours', store=True)
    # Nota: Se podría calcular dinámicamente con access_request_ids
    call_room_hours_used = fields.Float(string='Horas Call Room Usadas (Mes)', default=0.0)
    call_room_hours_remaining = fields.Float(string='Horas Call Room Disp.',
                                              compute='_compute_call_room_remaining')
    
    # Depósito de seguridad
    deposit_id = fields.Many2one('cowork.security.deposit', string='Depósito de Seguridad')
    deposit_required = fields.Boolean(related='plan_id.requires_deposit')
    
    # Facturación
    invoice_ids = fields.Many2many('account.move', string='Facturas', copy=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    amount_total = fields.Monetary(string='Monto Total', compute='_compute_amounts',
                                    currency_field='currency_id')
    amount_paid = fields.Monetary(string='Monto Pagado', compute='_compute_amounts',
                                   currency_field='currency_id')
    amount_due = fields.Monetary(string='Monto Pendiente', compute='_compute_amounts',
                                  currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    # Valoración
    rating_id = fields.Many2one('cowork.rating', string='Registro de Valoración')
    rating = fields.Selection(related='rating_id.rating', string='Valoración')
    
    # Notas
    notes = fields.Html(string='Notas Internas')
    requirements = fields.Text(string='Requisitos Especiales')
    
    # Responsable
    user_id = fields.Many2one('res.users', string='Responsable',
                               default=lambda self: self.env.user, tracking=True)
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    # Campos para portal
    access_token = fields.Char(string='Token de Acceso', copy=False)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cowork.membership') or _('Nuevo')
        records = super().create(vals_list)
        # Marcar al contacto como miembro
        for record in records:
            record.partner_id.write({'is_cowork_member': True})
        return records
    
    @api.depends('plan_id', 'date_start')
    def _compute_date_end(self):
        for record in self:
            if record.plan_id and record.date_start:
                duration_days = record.plan_id._get_duration_days()
                record.date_end = record.date_start + relativedelta(days=duration_days)
            else:
                record.date_end = False
    
    @api.depends('plan_id.credits_included')
    def _compute_credits(self):
        for record in self:
            record.credits_granted = record.plan_id.credits_included if record.plan_id else 0

    def action_view_rented_floor(self):
        self.ensure_one()
        if not self.floor_id:
            return True
        return {
            'type': 'ir.actions.act_window',
            'name': _('Piso Alquilado'),
            'res_model': 'cowork.floor',
            'view_mode': 'form',
            'res_id': self.floor_id.id,
            'target': 'current',
        }
    
    @api.depends('access_request_ids.credits_used', 'access_request_ids.state')
    def _compute_credits_used(self):
        for record in self:
            record.credits_used = sum(
                record.access_request_ids.filtered(
                    lambda r: r.state == 'approved' and r.payment_method == 'credits'
                ).mapped('credits_used')
            )
    
    @api.depends('credits_granted', 'credits_used')
    def _compute_credits_remaining(self):
        for record in self:
            # Incluir créditos adicionales comprados y renovaciones
            additional_credits = sum(self.env['cowork.credits'].search([
                ('partner_id', '=', record.partner_id.id),
                ('credits_type', 'in', ['purchased', 'bonus', 'renewal']),
            ]).mapped('credits_amount'))
            record.credits_remaining = record.credits_granted + additional_credits - record.credits_used
    
    @api.depends('plan_id.passes_included')
    def _compute_passes(self):
        for record in self:
            record.passes_granted = record.plan_id.passes_included if record.plan_id else 0

    @api.depends('passes_granted', 'passes_used')
    def _compute_passes_remaining(self):
        for record in self:
             record.passes_remaining = record.passes_granted - record.passes_used

    @api.depends('plan_id.call_room_hours_included')
    def _compute_call_room_hours(self):
        for record in self:
            record.call_room_hours_granted = record.plan_id.call_room_hours_included if record.plan_id else 0
            
    @api.depends('call_room_hours_granted', 'call_room_hours_used')
    def _compute_call_room_remaining(self):
        for record in self:
            record.call_room_hours_remaining = max(0.0, record.call_room_hours_granted - record.call_room_hours_used)
    
    @api.depends('access_request_ids')
    def _compute_access_request_count(self):
        for record in self:
            record.access_request_count = len(record.access_request_ids)
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
    
    @api.depends('invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.state')
    def _compute_amounts(self):
        for record in self:
            invoices = record.invoice_ids.filtered(lambda i: i.state == 'posted')
            record.amount_total = sum(invoices.mapped('amount_total'))
            record.amount_due = sum(invoices.mapped('amount_residual'))
            record.amount_paid = record.amount_total - record.amount_due
    
    def action_confirm(self):
        """Confirmar la membresía"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Solo se pueden confirmar membresías en estado borrador.'))
            
            # Verificar políticas
            if record.plan_id.policy_ids and not record.policies_accepted:
                raise UserError(_('El miembro debe aceptar las políticas antes de confirmar.'))
            
            # Asignar espacio
            if record.space_type == 'coworking' and record.desk_id:
                record.desk_id.write({
                    'state': 'reserved',
                    'member_id': record.partner_id.id,
                    'membership_id': record.id,
                })
            elif record.space_type == 'coliving' and record.bed_id:
                record.bed_id.write({
                    'state': 'reserved',
                    'member_id': record.partner_id.id,
                    'membership_id': record.id,
                })
            
            # Asignar Piso Exclusivo
            if record.plan_id.allows_exclusive_floor and record.floor_id:
                if record.floor_id.state != 'available':
                     raise UserError(_('El piso seleccionado ya no está disponible.'))
                
                record.floor_id.write({
                    'state': 'rented',
                    'member_id': record.partner_id.id,
                    'date_start': record.date_start,
                    'date_end': record.date_end,
                })
            
            record.write({'state': 'confirmed'})
            
            # Registrar créditos otorgados
            if record.credits_granted > 0:
                self.env['cowork.credits'].create({
                    'partner_id': record.partner_id.id,
                    'membership_id': record.id,
                    'credits_type': 'granted',
                    'credits_amount': record.credits_granted,
                    'description': _('Créditos del plan %s') % record.plan_id.name,
                })
    
    def action_create_invoice(self):
        """Crear factura para la membresía"""
        self.ensure_one()
        
        if not self.plan_id.product_id:
            # Intentar crear el producto si falta
            self.plan_id._create_or_update_product()
            if not self.plan_id.product_id:
                raise UserError(_('El plan no tiene un producto configurado para facturación.'))
        
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.plan_id.product_id.id,
                'name': _('Membresía %s - %s') % (self.name, self.plan_id.name),
                'quantity': 1,
                'price_unit': self.plan_id.price,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_ids = [(4, invoice.id)]
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factura',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }
    
    def action_create_subscription(self):
        """Crear presupuesto/suscripción de venta"""
        self.ensure_one()
        
        if not self.plan_id.product_id:
            self.plan_id._create_or_update_product()
            if not self.plan_id.product_id:
                raise UserError(_('El plan no tiene un producto configurado.'))
            
        sale_order_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'order_line': [(0, 0, {
                'product_id': self.plan_id.product_id.id,
                'name': _('Membresía %s - %s') % (self.name, self.plan_id.name),
                'product_uom_qty': 1,
                'price_unit': self.plan_id.price,
            })],
        }
        
        # Integración opcional con sale_subscription si existe el campo
        if self.plan_id.duration_type in ['monthly', 'annual']:
            # Nota: Esto es genérico, la implementación de suscripciones
            # varía según la versión y módulos instalados
            pass
            
        sale_order = self.env['sale.order'].create(sale_order_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Presupuesto',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
        }
    
    def action_activate(self):
        """Activar la membresía tras el pago"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Solo se pueden activar membresías confirmadas.'))
            
            # Cambiar estado del espacio a ocupado
            if record.desk_id:
                record.desk_id.write({'state': 'occupied'})
            elif record.bed_id:
                record.bed_id.write({'state': 'occupied'})
            
            # Piso exclusivo ya se marca como 'rented' en confirm, no cambia estado extra en active?
            # En cowork_floor definimos state: available, rented, maintenance. 'rented' es correcto.
            
            record.write({'state': 'active'})
    
    def action_expire(self):
        """Marcar membresía como expirada"""
        for record in self:
            # Liberar espacio
            if record.desk_id:
                record.desk_id.action_set_available()
            elif record.bed_id:
                record.bed_id.action_set_available()
            
            if record.floor_id:
                record.floor_id.write({
                    'state': 'available',
                    'member_id': False,
                    'date_start': False,
                    'date_end': False,
                })
            
            record.write({'state': 'expired'})
    
    def action_cancel(self):
        """Cancelar membresía"""
        for record in self:
            # Liberar espacio
            if record.desk_id:
                record.desk_id.action_set_available()
            elif record.bed_id:
                record.bed_id.action_set_available()
            
            if record.floor_id:
                record.floor_id.write({
                    'state': 'available',
                    'member_id': False,
                    'date_start': False,
                    'date_end': False,
                })
            
            record.write({'state': 'cancelled'})
    
    def action_renew(self):
        """Renovar membresía"""
        self.ensure_one()
        
        new_membership = self.copy({
            'date_start': self.date_end,
            'state': 'draft',
            'invoice_ids': False,
            'access_request_ids': False,
            'rating_id': False,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nueva Membresía',
            'res_model': 'cowork.membership',
            'res_id': new_membership.id,
            'view_mode': 'form',
        }
    
    def action_send_email(self):
        """Enviar detalles de membresía por email"""
        self.ensure_one()
        template = self.env.ref('aureofy_cowork_ll.email_template_membership_confirmation', 
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return True
    
    def action_send_rating_request(self):
        """Enviar solicitud de valoración"""
        self.ensure_one()
        template = self.env.ref('aureofy_cowork_ll.email_template_rating_request',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return True
    
    def action_view_invoices(self):
        """Ver facturas relacionadas"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facturas',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }
    
    def action_view_access_requests(self):
        """Ver solicitudes de acceso"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitudes de Acceso',
            'res_model': 'cowork.access.request',
            'view_mode': 'tree,form,kanban,calendar',
            'domain': [('membership_id', '=', self.id)],
            'context': {'default_membership_id': self.id},
        }
    
        for membership in to_remind:
            membership.action_send_renewal_reminder()
            
    @api.model
    def _cron_monthly_renewal_benefits(self):
        """Cron job para renovar créditos y pases mensualmente en membresías recurrentes"""
        today = fields.Date.today()
        # Buscar membresías activas y recurrentes
        active_recurring = self.search([
            ('state', '=', 'active'),
            ('plan_id.is_recurring', '=', True),
        ])
        
        for membership in active_recurring:
            # Verificar si hoy es el día de renovación (mismo día del mes que start_date)
            # Simplificación: si el día coincide.
            if membership.date_start.day == today.day:
                membership.action_renew_monthly_benefits()
                
    def action_renew_monthly_benefits(self):
        """Renovar beneficios mensuales (Créditos, Pases)"""
        for record in self:
            # 1. Renovar Créditos: Agregar créditos del plan nuevamente
            # Nota: Esto suma al total otorgado. El cálculo de remaining debe considerar
            # que los créditos "viejos" del plan quizás expiraron si no son acumulables.
            # Según requerimiento: "se renuevan mensualmente". Asumimos reset o grant nuevo.
            # Vamos a optar por GRANT nuevo para que quede registro.
            
            if record.plan_id.credits_included > 0:
                self.env['cowork.credits'].create({
                    'partner_id': record.partner_id.id,
                    'membership_id': record.id,
                    'credits_type': 'renewal',
                    'credits_amount': record.plan_id.credits_included,
                    'description': _('Renovación mensual de créditos plan %s') % record.plan_id.name,
                })
                # Actualizar el campo computado o store si es necesario. 
                # credits_granted en este modelo es un compute store del plan, asi que quizás
                # debamos ajustar la lógica de credits_remaining para que tome TODOS los grants
                # vinculados a la membresía, no solo el static del plan.
                
            # 2. Renovar Pases (Resetear usados o acumular?)
            # "Vienen con pases". Típicamente son mensuales "use it or lose it".
            record.write({
                'passes_used': 0, # Resetear consumo del mes
                'call_room_hours_used': 0.0 # Resetear consumo
            })
            
            record.message_post(body=_("Beneficios mensuales renovados (Pases y Horas reseteados, Créditos otorgados)."))
    
    def action_send_renewal_reminder(self):
        """Enviar recordatorio de renovación"""
        self.ensure_one()
        template = self.env.ref('aureofy_cowork_ll.email_template_renewal_reminder',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return True
    
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Membresia-%s' % self.name
