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
            # Incluir créditos adicionales comprados
            additional_credits = sum(self.env['cowork.credits'].search([
                ('partner_id', '=', record.partner_id.id),
                ('credits_type', 'in', ['purchased', 'bonus']),
            ]).mapped('credits_amount'))
            record.credits_remaining = record.credits_granted + additional_credits - record.credits_used
    
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
            
            record.write({'state': 'active'})
    
    def action_expire(self):
        """Marcar membresía como expirada"""
        for record in self:
            # Liberar espacio
            if record.desk_id:
                record.desk_id.action_set_available()
            elif record.bed_id:
                record.bed_id.action_set_available()
            
            record.write({'state': 'expired'})
    
    def action_cancel(self):
        """Cancelar membresía"""
        for record in self:
            # Liberar espacio
            if record.desk_id:
                record.desk_id.action_set_available()
            elif record.bed_id:
                record.bed_id.action_set_available()
            
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
    
    @api.model
    def _cron_check_expiry(self):
        """Cron job para verificar vencimientos"""
        today = fields.Date.today()
        
        # Buscar expiradas
        expired_memberships = self.search([
            ('state', '=', 'active'),
            ('date_end', '<', today),
        ])

        for membership in expired_memberships:
            # Guardamos el plan y si tiene auto-renew antes de expirar
            auto_renew = membership.plan_id.auto_renew
            
            # Expirar membresía actual (libera recursos)
            membership.action_expire()
            
            if auto_renew:
                # Renovar automáticamente
                res = membership.action_renew()
                if res and res.get('res_id'):
                    new_membership = self.browse(res['res_id'])
                    
                    # Aceptar políticas implícitamente al renovar
                    new_membership.write({'policies_accepted': True})
                    
                    try:
                        # Confirmar (asigna recursos y créditos)
                        new_membership.action_confirm()
                        
                        # Activar inmediatamente si es renovación continua?
                        # Generalmente se espera el pago, pero si es auto-renovación
                        # y tiene créditos, quizás se asume confianza o se genera factura.
                        # Vamos a crear la suscripción/orden de venta para el cobro.
                        new_membership.action_create_subscription()
                        
                        # Opcional: Notificar renovación
                        # new_membership.message_post(body=_("Renovación automática exitosa."))
                    except Exception as e:
                        new_membership.message_post(body=_("Error en renovación automática: %s") % str(e))
        
        # Enviar recordatorios de renovación (para las que vencen en 7 días)
        reminder_date = today + relativedelta(days=7)
        to_remind = self.search([
            ('state', '=', 'active'),
            ('date_end', '=', reminder_date),
            ('plan_id.auto_renew', '=', False) # Solo si no es automática? O avisar igual? Avisar igual.
        ])
        for membership in to_remind:
            membership.action_send_renewal_reminder()
    
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
