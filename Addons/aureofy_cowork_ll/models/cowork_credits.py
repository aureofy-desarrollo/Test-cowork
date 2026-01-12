# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class CoworkCredits(models.Model):
    _name = 'cowork.credits'
    _description = 'Créditos de Miembro'
    _order = 'date desc, id desc'

    partner_id = fields.Many2one('res.partner', string='Miembro', required=True,
                                  index=True, ondelete='cascade')
    membership_id = fields.Many2one('cowork.membership', string='Membresía',
                                     help='Membresía asociada si aplica')
    
    credits_type = fields.Selection([
        ('granted', 'Otorgados por Plan'),
        ('purchased', 'Comprados'),
        ('used', 'Usados'),
        ('refund', 'Reembolso'),
        ('bonus', 'Bonificación'),
        ('renewal', 'Renovación Mensual'),
        ('expired', 'Expirados'),
    ], string='Tipo', required=True)
    
    credits_amount = fields.Integer(string='Cantidad de Créditos', required=True,
                                     help='Positivo para agregar, negativo para usar')
    
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    
    description = fields.Char(string='Descripción')
    
    # Expiración
    date_expiration = fields.Date(string='Fecha de Vencimiento')
    
    # Para compras de créditos
    invoice_id = fields.Many2one('account.move', string='Factura')
    sale_id = fields.Many2one('sale.order', string='Orden de Venta')
    price_per_credit = fields.Monetary(string='Precio por Crédito', currency_field='currency_id')
    total_amount = fields.Monetary(string='Monto Total', compute='_compute_total_amount',
                                    currency_field='currency_id', store=True)
    
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    @api.depends('credits_amount', 'price_per_credit')
    def _compute_total_amount(self):
        for record in self:
            if record.credits_type == 'purchased' and record.price_per_credit:
                record.total_amount = record.credits_amount * record.price_per_credit
            else:
                record.total_amount = 0
    
    @api.model
    def get_partner_balance(self, partner_id):
        """Obtener balance de créditos de un partner"""
        credits = self.search([('partner_id', '=', partner_id)])
        return sum(credits.mapped('credits_amount')) or 0
    
    @api.model
    def purchase_credits(self, partner_id, amount, price_per_credit, validity_years=1):
        """Comprar créditos para un miembro"""
        
        date_expiration = False
        if validity_years:
            date_expiration = fields.Date.today() + relativedelta(years=validity_years)
            
        # Crear registro de créditos
        credit = self.create({
            'partner_id': partner_id,
            'credits_type': 'purchased',
            'credits_amount': amount,
            'price_per_credit': price_per_credit,
            'description': _('Compra de %s créditos') % amount,
            'date_expiration': date_expiration,
        })
        
        # Crear factura
        partner = self.env['res.partner'].browse(partner_id)
        product = self.env.ref('aureofy_cowork_ll.product_credits', raise_if_not_found=False)
        
        if product:
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': partner_id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': _('Compra de %s créditos para coworking') % amount,
                    'quantity': amount,
                    'price_unit': price_per_credit,
                })],
            }
            invoice = self.env['account.move'].create(invoice_vals)
            credit.invoice_id = invoice
        
        return credit


class CoworkCreditPackage(models.Model):
    _name = 'cowork.credit.package'
    _description = 'Paquete de Créditos'
    _order = 'sequence, credits_amount'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    credits_amount = fields.Integer(string='Cantidad de Créditos', required=True)
    price = fields.Monetary(string='Precio', required=True, currency_field='currency_id')
    price_per_credit = fields.Monetary(string='Precio por Crédito', 
                                        compute='_compute_price_per_credit',
                                        currency_field='currency_id')
    
    validity_years = fields.Integer(string='Validez (Años)', default=1,
                                     help='Años de vigencia de los créditos comprados.')
    
    discount_percentage = fields.Float(string='Descuento (%)',
                                        help='Descuento aplicado respecto al precio por crédito base')
    
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                   default=lambda self: self.env.company.currency_id)
    
    product_id = fields.Many2one('product.product', string='Producto')
    
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company)
    
    @api.depends('credits_amount', 'price')
    def _compute_price_per_credit(self):
        for record in self:
            if record.credits_amount:
                record.price_per_credit = record.price / record.credits_amount
            else:
                record.price_per_credit = 0
