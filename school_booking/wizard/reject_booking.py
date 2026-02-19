from odoo import fields, models, _
from odoo.exceptions import AccessError


class SchoolBookingRejectWizard(models.TransientModel):
    _name = 'school.booking.reject.wizard'
    _description = 'Asistente de Rechazo de Reserva'

    booking_id = fields.Many2one('school.booking', string='Reserva', required=True)
    reason = fields.Text(string='Motivo del Rechazo', required=True)

    def action_reject_confirm(self):
        self.ensure_one()
        user = self.env.user
        can_reject = self.env.uid == 1 or user.has_group('base.group_system') or \
            user.has_group('school_booking.group_school_booking_manager')
        if not can_reject:
            raise AccessError(_('Solo manager o admin pueden rechazar reservas.'))
        booking = self.booking_id
        booking.write({
            'state': 'rejected',
            'notes': (booking.notes or '') + "\n--- RECHAZADO ---\nMotivo: %s" % self.reason,
        })
        booking.message_post(
            body="<b>Reserva Rechazada</b><br/>Motivo: %s" % self.reason,
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}
