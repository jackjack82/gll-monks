from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    internal_location_id = fields.Many2one(
        "stock.location",
        string="Internal Location",
    )
