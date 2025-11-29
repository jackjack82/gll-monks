# © 2025 webmonks

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    service_for_box_id = fields.Many2one(
        "product.product",
        string="Servizio per scatola",
        domain=[("type", "=", "service")],
        config_parameter="gll_stock_management.service_for_box_id",
    )

    service_for_single_id = fields.Many2one(
        "product.product",
        string="Servizio per prodotto singolo",
        domain=[("type", "=", "service")],
        config_parameter="gll_stock_management.service_for_single_id",
    )
