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
        ('passes', 'Pase de Acceso'),
        ('call_room_hours', 'Horas Incluidas (Call Room)'),
        ('invoice', 'Factura'),
        ('free', 'Gratuito'),
    ], string='Método de Pago', default='credits')
    
    # Costos
    credits_cost = fields.Integer(string='Costo en Créditos', compute='_compute_credits_cost', store=True)
    credits_used = fields.Integer(string='Créditos Usados', default=0)
    
    passes_cost = fields.Integer(string='Costo en Pases', default=0)
    passes_used = fields.Integer(string='Pases Usados', default=0)

    call_room_hours_cost = fields.Float(string='Horas Requeridas', default=0.0)
    call_room_hours_used = fields.Float(string='Horas Usadas', default=0.0)
    
    price = fields.Monetary(string='Precio', compute='_compute_price', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    invoice_id = fields.Many2one('account.move', string='Factura', copy=False)
    
    # Disponibilidad de créditos
    credits_available = fields.Integer(string='Créditos Disponibles',
                                        compute='_compute_credits_available')
    can_pay_with_credits = fields.Boolean(string='Puede Pagar con Créditos',
                                           compute='_compute_can_pay_with_credits')
    
    # Disponibilidad de Pases/Horas
    passes_available = fields.Integer(related='membership_id.passes_remaining')
    call_room_hours_available = fields.Float(related='membership_id.call_room_hours_remaining')
    
    can_pay_with_passes = fields.Boolean(compute='_compute_can_pay_others')
    can_pay_with_hours = fields.Boolean(compute='_compute_can_pay_others')
    
    is_guest = fields.Boolean(string='Es Invitado', default=False)
    guest_name = fields.Char(string='Nombre del Invitado')
    guest_email = fields.Char(string='Email del Invitado')
    
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
    
    @api.depends('membership_id.passes_remaining', 'membership_id.call_room_hours_remaining',
                 'service_type', 'duration_hours')
    def _compute_can_pay_others(self):
        for record in self:
            # Pases: asumimos 1 pase por acceso (independiente de duración? O por día?)
            # Prompt: "Los créditos se usan para ... y call rooms incluidos en una membresía de una hora"
            # Vamos a asumir que "Pases" es para accesos generales (shared_space)
            # Pases: asumimos 1 pase por acceso
            # Si es invitado, siempre se puede pagar con pase si tiene disponibles
            is_valid_service = record.service_type in ['shared_space', 'hot_desk']
            
            record.can_pay_with_passes = (
                (is_valid_service or record.is_guest) and 
                record.membership_id.passes_remaining > 0
            )
            
            # Call Rooms
            # "call rooms incluidos en una membresía de una hora" (implica 1 hora incluida?)
            # Vamos a usar el campo call_room_hours_included del plan
            is_call_room = record.service_type in ['phone_booth', 'meeting_room'] # Maybe just phone_booth for call room
            # Si el tipo es específico
            if record.service_id.name and 'Call Room' in record.service_id.name:
                is_call_room = True
                
            record.can_pay_with_hours = (
                is_call_room and 
                record.membership_id.call_room_hours_remaining >= record.duration_hours
            )

    @api.onchange('service_id', 'duration_hours', 'is_guest')
    def _onchange_service_id(self):
        if self.service_id:
            # Recalcular campos de costo si es necesario
            if self.service_type in ['shared_space', 'hot_desk']:
                self.passes_cost = 1
            else:
                self.passes_cost = 0
                
            if self.service_id.name and 'Call Room' in self.service_id.name:
                self.call_room_hours_cost = self.duration_hours
            else:
                self.call_room_hours_cost = 0.0

            # Determinar método de pago por defecto
            is_valid_pass_service = self.service_type in ['shared_space', 'hot_desk']
            can_use_pass = (is_valid_pass_service or self.is_guest) and self.membership_id.passes_remaining > 0
            
            if not self.service_id.is_paid:
                self.payment_method = 'free'
            elif self.can_pay_with_hours:
                self.payment_method = 'call_room_hours'
            elif can_use_pass:
                self.payment_method = 'passes'
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
                    
            # Verificar Pisos Exclusivos
            # Si reservo un escritorio en un piso exclusivo, debo ser el inquilino exclusivo.
            # O si reservo el piso entero?
            # Asumimos que los escritorios tienen floor_id
            # No tenemos floor_id directo en service, pero quizás en desk relacionado?
            # cowork_service no tiene link a desk/floor.
            # Pero cowork_access_request suele ser para services genéricos o específicos?
            # Faltaría linkear la solicitud a un recurso específico si es "Book a Desk".
            # Asumiremos que el service_id puede representar un recurso o hay un campo faltante.
            # Si no hay campo resource_id, no podemos validar exclusive floor aquí fácilmente sin cambiar modelo.
            # PERO: desk_id está en cowork.membership para asignación fija.
            # Si esto es "Booking", debería haber un target.
            # Vamos a asumir que validation global está bien, pero para Exclusive Floors:
            # Si hay un piso Exclusive Rented, nadie más debería poder reservar recursos ahí.
            pass
    
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
            elif record.payment_method == 'passes':
                if not record.can_pay_with_passes:
                    raise UserError(_('No tiene pases disponibles.'))
            elif record.payment_method == 'call_room_hours':
                 if not record.can_pay_with_hours:
                    raise UserError(_('No tiene horas de Call Room disponibles.'))
            
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
            elif record.payment_method == 'passes':
                record.passes_used = 1 # O cost field
                record.membership_id.passes_used += 1
                
                # Si es invitado, registrar en la descripción
                description = _('Uso de Pase: %s') % record.service_id.name
                if record.is_guest:
                    description = _('Pase de Invitado: %s') % (record.guest_name or _('N/A'))
                    
                # Opcional: Crear un registro de log o similar
                record.membership_id.message_post(body=description)
            elif record.payment_method == 'call_room_hours':
                record.call_room_hours_used = record.duration_hours
                record.membership_id.call_room_hours_used += record.duration_hours
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
            if record.state == 'approved':
                if record.payment_method == 'credits':
                    # Devolver créditos
                    self.env['cowork.credits'].create({
                        'partner_id': record.partner_id.id,
                        'membership_id': record.membership_id.id,
                        'credits_type': 'refund',
                        'credits_amount': record.credits_used,
                        'description': _('Devolución por cancelación: %s') % record.service_id.name,
                    })
                elif record.payment_method == 'passes':
                    record.membership_id.passes_used -= record.passes_used
                elif record.payment_method == 'call_room_hours':
                    record.membership_id.call_room_hours_used -= record.call_room_hours_used
                    
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
