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
        default=1.0,
    )
    price = fields.Float(
        string="Price",
    )
    total = fields.Float(
        string="Total",
        compute="_compute_total",
        store=True,
    )

    @api.depends("quantity", "price")
    def _compute_total(self):
        for service in self:
            service.total = service.quantity * service.price