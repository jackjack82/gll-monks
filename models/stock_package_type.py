from odoo import fields, models


class PackageType(models.Model):
    _inherit = "stock.package.type"

    receipts_product_id = fields.Many2one(
        "product.product",
        string="Receipts Package Product",
        required=True,
    )

    deliveries_product_id = fields.Many2one(
        "product.product",
        string="Deliveries Package Product",
        required=True,
    )

    def get_order_product_id(self, operation_type):
        """This method retuns the product related to the
        package type, depending on transfer type"""
        if operation_type == "receipts":
            return self.receipts_product_id
        if operation_type == "deliveries":
            return self.deliveries_product_id
        else:
            return False
