# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CoworkAccessRequest(models.Model):
    _name = 'cowork.access.request'
    _description = 'Solicitud de Acceso a Servicio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False,
                       default=lambda self: _('Nuevo'))
    
    membership_id = fields.Many2one('cowork.membership', string='Membresía',
                                     required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Miembro',
                                  related='membership_id.partner_id', store=True)
    
    service_id = fields.Many2one('cowork.service', string='Servicio Solicitado',
                                  required=True, domain=[('is_paid', '=', True)])
    service_type = fields.Selection(related='service_id.service_type', store=True)
    
    date_request = fields.Datetime(string='Fecha de Solicitud', 
                                    default=fields.Datetime.now, readonly=True)
    date_scheduled = fields.Datetime(string='Fecha Programada', required=True)
    duration_hours = fields.Float(string='Duración (horas)', default=1.0)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft', tracking=True)
    
    # Método de pago
    payment_method = fields.Selection([
        ('credits', 'Créditos'),
        ('invoice', 'Factura'),
        ('free', 'Gratuito'),
    ], string='Método de Pago', default='credits')
    
    # Costos
    credits_cost = fields.Integer(string='Costo en Créditos', compute='_compute_credits_cost', store=True)
    credits_used = fields.Integer(string='Créditos Usados', default=0)
    
    price = fields.Monetary(string='Precio', compute='_compute_price', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    invoice_id = fields.Many2one('account.move', string='Factura', copy=False)
    
    # Disponibilidad de créditos
    credits_available = fields.Integer(string='Créditos Disponibles',
                                        compute='_compute_credits_available')
    can_pay_with_credits = fields.Boolean(string='Puede Pagar con Créditos',
                                           compute='_compute_can_pay_with_credits')
    
    notes = fields.Text(string='Notas')
    rejection_reason = fields.Text(string='Motivo de Rechazo')
    
    user_id = fields.Many2one('res.users', string='Aprobador')
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cowork.access.request') or _('Nuevo')
        return super().create(vals_list)
    
    @api.depends('membership_id.credits_remaining')
    def _compute_credits_available(self):
        for record in self:
            record.credits_available = record.membership_id.credits_remaining if record.membership_id else 0
    
    @api.depends('credits_available', 'credits_cost', 'service_id.allow_credit_payment')
    def _compute_can_pay_with_credits(self):
        for record in self:
            record.can_pay_with_credits = (
                record.service_id.allow_credit_payment and 
                record.credits_available >= record.credits_cost
            )
    
    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            if not self.service_id.is_paid:
                self.payment_method = 'free'
            elif self.can_pay_with_credits:
                self.payment_method = 'credits'
            else:
                self.payment_method = 'invoice'

    @api.depends('service_id.price', 'duration_hours')
    def _compute_price(self):
        for record in self:
            price = 0.0
            if record.service_id and record.service_id.price:
                price = record.service_id.price * record.duration_hours
            record.price = price

    @api.depends('service_id.credits_cost', 'duration_hours')
    def _compute_credits_cost(self):
        for record in self:
            credits = 0
            if record.service_id and record.service_id.credits_cost:
                # Assuming simple multiplication like price. 
                # service_id.credits_cost is likely "per hour" or "base cost". 
                # Given the user request implies scaling by duration explicitly:
                credits = int(record.service_id.credits_cost * record.duration_hours)
            record.credits_cost = credits

    @api.constrains('service_id', 'date_scheduled', 'duration_hours', 'state')
    def _check_overlap(self):
        for record in self:
            if record.state in ['rejected', 'cancelled'] or not record.date_scheduled:
                continue
            
            start_date = record.date_scheduled
            end_date = start_date + timedelta(hours=record.duration_hours)
            
            domain = [
                ('id', '!=', record.id),
                ('service_id', '=', record.service_id.id),
                ('state', 'not in', ['rejected', 'cancelled']),
                ('date_scheduled', '<', end_date),
            ]
            
            overlap_candidates = self.search(domain)
            for candidate in overlap_candidates:
                candidate_end = candidate.date_scheduled + timedelta(hours=candidate.duration_hours)
                if candidate_end > start_date:
                    raise ValidationError(_('El servicio ya está reservado para este horario.'))
    
    def action_submit(self):
        """Enviar solicitud para aprobación"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Solo se pueden enviar solicitudes en borrador.'))
            
            # Verificar disponibilidad de créditos si es método de pago
            if record.payment_method == 'credits':
                if not record.can_pay_with_credits:
                    raise UserError(_('No tiene suficientes créditos disponibles. '
                                     'Disponible: %s, Requerido: %s') % 
                                   (record.credits_available, record.credits_cost))
            
            record.write({'state': 'pending'})
            
            # Notificar al administrador
            record._send_admin_notification()
    
    def action_approve(self):
        """Aprobar la solicitud"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Solo se pueden aprobar solicitudes pendientes.'))
            
            if record.payment_method == 'credits':
                # Descontar créditos
                record.credits_used = record.credits_cost
                self.env['cowork.credits'].create({
                    'partner_id': record.partner_id.id,
                    'membership_id': record.membership_id.id,
                    'credits_type': 'used',
                    'credits_amount': -record.credits_cost,
                    'description': _('Uso de servicio: %s') % record.service_id.name,
                })
            elif record.payment_method == 'invoice':
                # Crear factura
                record._create_invoice()
            
            record.write({
                'state': 'approved',
                'user_id': self.env.uid,
            })
            
            # Notificar al miembro
            record._send_member_approval_notification()
    
    def action_reject(self):
        """Rechazar la solicitud"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Solo se pueden rechazar solicitudes pendientes.'))
            
            record.write({
                'state': 'rejected',
                'user_id': self.env.uid,
            })
            
            # Notificar al miembro
            record._send_member_rejection_notification()
    
    def action_cancel(self):
        """Cancelar la solicitud"""
        for record in self:
            if record.state == 'approved' and record.payment_method == 'credits':
                # Devolver créditos
                self.env['cowork.credits'].create({
                    'partner_id': record.partner_id.id,
                    'membership_id': record.membership_id.id,
                    'credits_type': 'refund',
                    'credits_amount': record.credits_used,
                    'description': _('Devolución por cancelación: %s') % record.service_id.name,
                })
            record.write({'state': 'cancelled'})
    
    def _create_invoice(self):
        """Crear factura para el servicio"""
        self.ensure_one()
        
        if not self.service_id.product_id:
            raise UserError(_('El servicio no tiene un producto configurado para facturación.'))
        
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.service_id.product_id.id,
                'name': _('%s - %s') % (self.service_id.name, self.name),
                'quantity': self.duration_hours,
                'price_unit': self.service_id.price,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice
        return invoice
    
    def _send_admin_notification(self):
        """Enviar notificación al administrador"""
        template = self.env.ref('aureofy_cowork_ll.email_template_access_request_admin',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    def _send_member_approval_notification(self):
        """Enviar notificación de aprobación al miembro"""
        template = self.env.ref('aureofy_cowork_ll.email_template_access_approved',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    def _send_member_rejection_notification(self):
        """Enviar notificación de rechazo al miembro"""
        template = self.env.ref('aureofy_cowork_ll.email_template_access_rejected',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
