from odoo import api, fields, models


class StockPackageType(models.Model):

    _inherit = "stock.package.type"

    size_id = fields.Many2one("stock.package.type.size", string="Size")