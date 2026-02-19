from odoo import fields, models


class SchoolRoom(models.Model):
    _name = 'school.room'
    _description = 'Aula / Recurso'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    capacity = fields.Integer(string='Capacidad', required=True, default=1)
    location = fields.Char(string='Ubicacion')
    active = fields.Boolean(string='Activo', default=True)
    notes = fields.Text(string='Notas')

    booking_ids = fields.One2many('school.booking', 'room_id', string='Reservas')
