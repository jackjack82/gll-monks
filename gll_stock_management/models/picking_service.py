from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .stock_picking import SERVICE_TYPE


class PickingService(models.Model):
    _name = "picking.service"
    _description = "Picking Service"

    picking_id = fields.Many2one(
        "stock.picking",
        string="Picking",
        required=True,
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
        SERVICE_TYPE,
        string="Service Type",
        copy=False,
        required=True,
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
    currency_id = fields.Many2one(
        related="sale_line_id.currency_id", store=True, string="Ordered"
    )
    so_amount = fields.Monetary(related="sale_line_id.price_subtotal", store=True)

    @api.depends("quantity", "price")
    def _compute_total(self):
        for service in self:
            service.total = service.quantity * service.price

    def unlink(self):
        """Delete also the sale order line related to this service.
        If this is not possible, you will get an error"""
        if self.sale_line_id:
            self.sale_line_id.unlink()
        res = super().unlink()
        return res

    def add_line_to_sale_order(self):
        """Add a line to the sale order if the sale_line_id is missing."""
        # todo: the line is added at the end, no matter the section
        sol_obj = self.env["sale.order.line"]
        order = self.picking_id.mapped("all_service_ids.sale_line_id.order_id")
        if len(order) != 1:
            raise UserError(
                _("A related Sale Order is either missing or there are too many.")
            )
        if order.state not in ["draft", "sent"]:
            raise UserError(
                _("You can not add a line to the sale order if it is not draft.")
            )
        so_line_id = sol_obj.create(
            {
                "product_id": self.product_id.id,
                "product_uom_qty": self.quantity,
                "price_unit": self.price,
                "order_id": order.id,
            },
        )
        self.sale_line_id = so_line_id

    # def create(self, vals_list):
    #     """getting the intrastat codes from product"""
    #     res = super(PickingService, self).create(vals_list)
    #     return res
