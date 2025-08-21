from odoo import api, fields, models


class PickingService(models.Model):
    _name = "picking.service"
    _description = "Picking Service"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Picking",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
    )
    quantity = fields.Float(
        string="Quantity",
        default=0.0,
    )
    price = fields.Float(
        string="Price",
    )
    pick_service_type = fields.Selection(
        [
            ("warehouse", "Warehouse"),
            ("transport", "Transport"),
            ("accessories", "Accessories"),
            ("additional", "Additional"),
            ("fixed", "Fixed"),
            ("variable", "Variable"),
        ],
        string="Service Type",
        copy=False,
    )
    total = fields.Float(
        string="Total",
        compute="_compute_total",
        store=True,
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="SO line",
    )
    currency_id = fields.Many2one(related="sale_line_id.currency_id", store=True, string="Ordered")
    so_amount = fields.Monetary(related="sale_line_id.price_subtotal", stored=True)

    @api.depends("quantity", "price")
    def _compute_total(self):
        for service in self:
            service.total = service.quantity * service.price

    def unlink(self):
        """Delete also the sale order line related to this service.
        If this is not possible, you will get an error"""
        # todo: also consider cases of setting qty to zero
        self.so_line_id.unlink()
        res = super().unlink()
        return res