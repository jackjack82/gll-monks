from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    package_type_id = fields.Many2one(
        related="result_package_id.package_type_id",
        string="Package Type",
        readonly=False,
    )