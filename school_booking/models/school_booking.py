from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class SchoolBooking(models.Model):
    _name = 'school.booking'
    _description = 'Reserva de Aula'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_dt desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nuevo'))
    room_id = fields.Many2one('school.room', string='Aula/Recurso', required=True, tracking=True)
    requester_id = fields.Many2one('res.users', string='Solicitante',
                                   default=lambda self: self.env.user, tracking=True)
    attendee_ids = fields.Many2many('res.users', string='Participantes')

    start_dt = fields.Datetime(string='Inicio', required=True, tracking=True,
                               default=fields.Datetime.now)
    end_dt = fields.Datetime(string='Fin', required=True, tracking=True,
                             default=lambda self: fields.Datetime.now() + timedelta(hours=1))
    duration_hours = fields.Float(string='Horas', compute='_compute_duration', store=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', 'Esperando Aprobacion'),
        ('approved', 'Confirmada'),
        ('rejected', 'Rechazada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft', tracking=True)

    notes = fields.Text(string='Notas')

    def _can_approve_or_reject(self):
        user = self.env.user
        return self.env.uid == 1 or user.has_group('base.group_system') or \
            user.has_group('school_booking.group_school_booking_manager')

    @api.depends('start_dt', 'end_dt')
    def _compute_duration(self):
        for record in self:
            if record.start_dt and record.end_dt:
                diff = record.end_dt - record.start_dt
                record.duration_hours = diff.total_seconds() / 3600.0
            else:
                record.duration_hours = 0.0

    @api.constrains('room_id', 'start_dt', 'end_dt', 'state')
    def _check_overlap(self):
        for record in self:
            if record.start_dt and record.end_dt:
                if record.start_dt >= record.end_dt:
                    raise ValidationError(_('La fecha de inicio debe ser anterior a la de fin.'))
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('room_id', '=', record.room_id.id),
                    ('state', 'not in', ['rejected', 'cancelled']),
                    ('start_dt', '<', record.end_dt),
                    ('end_dt', '>', record.start_dt),
                ], limit=1)
                if overlapping:
                    raise ValidationError(_(
                        'Conflicto: El aula ya esta ocupada en este horario por la reserva %s.'
                    ) % overlapping.name)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('school.booking') or _('Nuevo')
        return super().create(vals)

    def write(self, vals):
        if 'state' in vals and vals['state'] in ('approved', 'rejected') and not self._can_approve_or_reject():
            raise AccessError(_('Solo manager o admin pueden aprobar o rechazar reservas.'))
        return super().write(vals)

    def action_confirm(self):
        self.write({'state': 'to_approve'})

    def action_approve(self):
        if not self._can_approve_or_reject():
            raise AccessError(_('Solo manager o admin pueden aprobar reservas.'))
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_open_reject_wizard(self):
        if not self._can_approve_or_reject():
            raise AccessError(_('Solo manager o admin pueden rechazar reservas.'))
        return {
            'name': _('Motivo de Rechazo'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.booking.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_booking_id': self.id},
        }
