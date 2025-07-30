from odoo import fields, models


class PackageType(models.Model):
    _inherit = "stock.package.type"

    sale_product_id = fields.Many2one(
        "product.product",
        string="Sale Package Product",
        required=True,
    )
