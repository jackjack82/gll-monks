from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Partner",
    )
    items_count = fields.Integer(
        compute="compute_items_count_volume",
        store=True,
        string="Number of packages",
    )
    items_volume = fields.Float(
        compute="compute_items_count_volume",
        store=True,
        string="Total volume (m2)",
    )

    @api.onchange("delivery_partner_id")
    def _onchange_delivery_partner(self):
        if self.delivery_partner_id and self.picking_type_code == "incoming":
            self.location_dest_id = self.delivery_partner_id.internal_location_id

    @api.depends("move_line_ids.quantity")
    def compute_items_count_volume(self):
        for picking in self:
            picking.items_volume = sum(
                sml.quantity * sml.product_id.volume for sml in self.move_line_ids
            )
            picking.items_count = len(self.move_ids.move_line_ids.result_package_id)
