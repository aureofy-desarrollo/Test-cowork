# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CoworkSecurityDeposit(models.Model):
    _name = 'cowork.security.deposit'
    _description = 'Depósito de Seguridad'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_created desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False,
                       default=lambda self: _('Nuevo'))
    
    membership_id = fields.Many2one('cowork.membership', string='Membresía',
                                     required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Miembro',
                                  related='membership_id.partner_id', store=True)
    
    amount = fields.Monetary(string='Monto', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    date_created = fields.Date(string='Fecha de Creación', default=fields.Date.today)
    date_paid = fields.Date(string='Fecha de Pago')
    date_returned = fields.Date(string='Fecha de Devolución')
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('returned', 'Devuelto'),
        ('withheld', 'Retenido'),
    ], string='Estado', default='pending', tracking=True)
    
    invoice_id = fields.Many2one('account.move', string='Factura de Depósito')
    refund_id = fields.Many2one('account.move', string='Nota de Crédito')
    
    notes = fields.Text(string='Notas')
    withhold_reason = fields.Text(string='Motivo de Retención')
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cowork.security.deposit') or _('Nuevo')
        return super().create(vals_list)
    
    def action_mark_paid(self):
        """Marcar como pagado"""
        self.write({
            'state': 'paid',
            'date_paid': fields.Date.today(),
        })
    
    def action_return(self):
        """Devolver depósito"""
        self.write({
            'state': 'returned',
            'date_returned': fields.Date.today(),
        })
    
    def action_withhold(self):
        """Retener depósito"""
        self.write({'state': 'withheld'})
