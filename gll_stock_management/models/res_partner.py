import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    internal_location_id = fields.Many2one("stock.location", string="Internal Location")