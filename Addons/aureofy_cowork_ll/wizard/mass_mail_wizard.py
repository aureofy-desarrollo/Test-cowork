# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MassMailWizard(models.TransientModel):
    _name = 'cowork.mass.mail.wizard'
    _description = 'Asistente de Envío Masivo de Email'

    membership_ids = fields.Many2many('cowork.membership', string='Membresías Seleccionadas')
    
    template_id = fields.Many2one('mail.template', string='Plantilla de Email',
                                   domain=[('model_id.model', '=', 'cowork.membership')])
    
    subject = fields.Char(string='Asunto')
    body = fields.Html(string='Contenido del Email')
    
    use_template = fields.Boolean(string='Usar Plantilla', default=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            res['membership_ids'] = [(6, 0, active_ids)]
        return res
    
    def action_send_mail(self):
        """Enviar email a todas las membresías seleccionadas"""
        self.ensure_one()
        
        for membership in self.membership_ids:
            if not membership.partner_id.email:
                continue
            
            if self.use_template and self.template_id:
                self.template_id.send_mail(membership.id, force_send=True)
            else:
                # Enviar email personalizado
                mail_values = {
                    'subject': self.subject,
                    'body_html': self.body,
                    'email_to': membership.partner_id.email,
                    'email_from': self.env.company.email or self.env.user.email,
                }
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Emails enviados correctamente a %s membresías.') % len(self.membership_ids),
                'type': 'success',
                'sticky': False,
            }
        }
