
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    picking_code = fields.Selection(
        string="Picking Type Code", store=True, related="picking_type_id.code"
    )
    current_package_id = fields.Many2one(
        "stock.quant.package", string="Current Package", copy=False
    )
    current_package_type_id = fields.Many2one(
        related="current_package_id.package_type_id", readonly=False, copy=False
    )
    pack_piece_count = fields.Integer(
        related="current_package_id.piece_count", string="Package Pieces"
    )