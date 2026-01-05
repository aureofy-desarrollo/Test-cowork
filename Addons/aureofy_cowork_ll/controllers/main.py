# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request


class CoworkWebsiteController(http.Controller):

    @http.route(['/cowork/request'], type='http', auth='public', website=True)
    def cowork_request(self, **kwargs):
        """Página de solicitud de espacio de coworking"""
        desk_types = [
            ('flexible', 'Puesto Flexible'),
            ('private_cabin', 'Cabina Privada'),
            ('meeting_room', 'Sala de Reuniones'),
            ('hot_desk', 'Hot Desk'),
        ]
        
        cities = request.env['cowork.floor'].sudo().search([]).mapped('city')
        cities = list(set([c for c in cities if c]))
        
        return request.render('aureofy_cowork_ll.website_cowork_request', {
            'desk_types': desk_types,
            'cities': cities,
        })

    @http.route(['/coliving/request'], type='http', auth='public', website=True)
    def coliving_request(self, **kwargs):
        """Página de solicitud de espacio de coliving"""
        bed_types = [
            ('single', 'Individual'),
            ('shared', 'Compartida'),
            ('bunk', 'Litera'),
            ('private_room', 'Habitación Privada'),
        ]
        
        cities = request.env['cowork.floor'].sudo().search([]).mapped('city')
        cities = list(set([c for c in cities if c]))
        
        return request.render('aureofy_cowork_ll.website_coliving_request', {
            'bed_types': bed_types,
            'cities': cities,
        })

    @http.route(['/cowork/search'], type='http', auth='public', website=True)
    def cowork_search(self, desk_type=None, city=None, **kwargs):
        """Búsqueda de espacios de coworking"""
        domain = [('state', '=', 'available')]
        if desk_type:
            domain.append(('desk_type', '=', desk_type))
        if city:
            domain.append(('city', 'ilike', city))
        
        desks = request.env['cowork.desk'].sudo().search(domain)
        plans = request.env['cowork.membership.plan'].sudo().search([
            ('space_type', '=', 'coworking'),
            ('active', '=', True),
        ])
        
        return request.render('aureofy_cowork_ll.website_cowork_results', {
            'desks': desks,
            'plans': plans,
            'desk_type': desk_type,
            'city': city,
        })

    @http.route(['/coliving/search'], type='http', auth='public', website=True)
    def coliving_search(self, bed_type=None, city=None, **kwargs):
        """Búsqueda de espacios de coliving"""
        domain = [('state', '=', 'available')]
        if bed_type:
            domain.append(('bed_type', '=', bed_type))
        if city:
            domain.append(('city', 'ilike', city))
        
        beds = request.env['cowork.bed'].sudo().search(domain)
        plans = request.env['cowork.membership.plan'].sudo().search([
            ('space_type', '=', 'coliving'),
            ('active', '=', True),
        ])
        
        return request.render('aureofy_cowork_ll.website_coliving_results', {
            'beds': beds,
            'plans': plans,
            'bed_type': bed_type,
            'city': city,
        })

    @http.route(['/cowork/submit'], type='http', auth='public', website=True, methods=['POST'])
    def cowork_submit(self, **post):
        """Procesar solicitud de coworking"""
        lead_vals = {
            'name': _('Solicitud Coworking - %s') % post.get('name', ''),
            'contact_name': post.get('name'),
            'email_from': post.get('email'),
            'phone': post.get('phone'),
            'is_cowork_lead': True,
            'space_type': 'coworking',
            'preferred_desk_type': post.get('desk_type'),
            'city_preference': post.get('city'),
            'preferred_start_date': post.get('start_date'),
            'special_requirements': post.get('requirements'),
        }
        
        request.env['crm.lead'].sudo().create(lead_vals)
        
        return request.redirect('/cowork/thanks')

    @http.route(['/coliving/submit'], type='http', auth='public', website=True, methods=['POST'])
    def coliving_submit(self, **post):
        """Procesar solicitud de coliving"""
        lead_vals = {
            'name': _('Solicitud Coliving - %s') % post.get('name', ''),
            'contact_name': post.get('name'),
            'email_from': post.get('email'),
            'phone': post.get('phone'),
            'is_cowork_lead': True,
            'space_type': 'coliving',
            'preferred_bed_type': post.get('bed_type'),
            'city_preference': post.get('city'),
            'preferred_start_date': post.get('start_date'),
            'special_requirements': post.get('requirements'),
        }
        
        request.env['crm.lead'].sudo().create(lead_vals)
        
        return request.redirect('/cowork/thanks')

    @http.route(['/cowork/thanks'], type='http', auth='public', website=True)
    def cowork_thanks(self, **kwargs):
        """Página de agradecimiento"""
        return request.render('aureofy_cowork_ll.website_thanks')
