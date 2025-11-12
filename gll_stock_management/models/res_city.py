# © 2025 webmonks

from odoo import fields, models


class City(models.Model):
    _inherit = 'res.city'

    inconvenient_place_ids = fields.Many2many(
        'delivery.carrier',
        'res_city_inconvenient_place_rel',
        'city_id',
        'carrier_id',
        string='Inconvenient Place',
        help='Delivery carriers that consider this city as an inconvenient place',
    )
    