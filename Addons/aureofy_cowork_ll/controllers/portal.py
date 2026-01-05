# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CoworkPortalController(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        if 'membership_count' in counters:
            values['membership_count'] = request.env['cowork.membership'].search_count([
                ('partner_id', '=', partner.id)
            ])
        
        return values

    @http.route(['/my/memberships', '/my/memberships/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_memberships(self, page=1, sortby=None, filterby=None, **kw):
        """Lista de membresías del usuario"""
        partner = request.env.user.partner_id
        Membership = request.env['cowork.membership']
        
        domain = [('partner_id', '=', partner.id)]
        
        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Fecha'), 'order': 'date_start desc'},
            'name': {'label': _('Número'), 'order': 'name'},
            'state': {'label': _('Estado'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Filters
        searchbar_filters = {
            'all': {'label': _('Todas'), 'domain': []},
            'active': {'label': _('Activas'), 'domain': [('state', '=', 'active')]},
            'expired': {'label': _('Expiradas'), 'domain': [('state', '=', 'expired')]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # Count
        membership_count = Membership.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url='/my/memberships',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=membership_count,
            page=page,
            step=10,
        )
        
        # Memberships
        memberships = Membership.search(domain, order=order, limit=10, offset=pager['offset'])
        
        values = {
            'memberships': memberships,
            'page_name': 'memberships',
            'pager': pager,
            'default_url': '/my/memberships',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        }
        
        return request.render('aureofy_cowork_ll.portal_my_memberships', values)

    @http.route(['/my/membership/<int:membership_id>'], type='http', auth='user', website=True)
    def portal_membership_detail(self, membership_id, **kw):
        """Detalle de una membresía"""
        partner = request.env.user.partner_id
        membership = request.env['cowork.membership'].browse(membership_id)
        
        if not membership.exists() or membership.partner_id != partner:
            return request.redirect('/my/memberships')
        
        values = {
            'membership': membership,
            'page_name': 'membership_detail',
        }
        
        return request.render('aureofy_cowork_ll.portal_membership_detail', values)

    @http.route(['/my/membership/<int:membership_id>/download'], type='http', auth='user', website=True)
    def portal_membership_download(self, membership_id, **kw):
        """Descargar PDF de membresía"""
        partner = request.env.user.partner_id
        membership = request.env['cowork.membership'].browse(membership_id)
        
        if not membership.exists() or membership.partner_id != partner:
            return request.redirect('/my/memberships')
        
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'aureofy_cowork_ll.action_report_membership', [membership.id]
        )
        
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename="Membresia-%s.pdf"' % membership.name),
        ]
        
        return request.make_response(pdf_content, headers=headers)
