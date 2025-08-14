from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    product_uom_qty = fields.Float(string="Quantity")
