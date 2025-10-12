# © 2025 webmonks

from odoo import api, fields, models


class GllTrip(models.Model):
    _name = "gll.trip"
    _description = "Trip"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _sequence = "gll.trip.sequence"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
        copy=False,
        default=lambda self: self.env["ir.sequence"].next_by_code("gll.trip.sequence"),
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Driver",
        required=True,
        tracking=True,
    )
    phone = fields.Char(string="Phone")
    vehicle_plate = fields.Char(string="Vehicle")
    note = fields.Text(string="Notes")
    picking_ids = fields.Many2many(
        "stock.picking",
        string="Deliveries",
        relation="stock_picking_gll_trip_rel",
        column1="trip_id",
        column2="picking_id",
        # todo: trip only contains done picks?
    )
    picking_count = fields.Integer(
        string="Delivery Count",
        compute="_compute_picking_count",
        store=True,
    )
    date_shipment = fields.Date(string="Date Shipment")
    tour = fields.Float(string="Tour (Eur)")
    date_load = fields.Date(string="Date Load")
    price = fields.Float(string="Price (Eur)")
    trip_type = fields.Selection(
        [
            ("distribution", "Distribution"),
        ]
    )

    @api.depends("picking_ids")
    def _compute_picking_count(self):
        for trip in self:
            trip.picking_count = len(trip.picking_ids)

    def action_view_pickings(self):
        """Open the tree view of the pickings associated with this trip"""
        self.ensure_one()
        action = {
            "name": "Deliveries",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", self.picking_ids.ids)],
        }
        return action

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """Override create method to generate sequence for name field"""
    #     for vals in vals_list:
    #         if vals.get("name", "/") == "/":
    #             vals["name"] = self.env["ir.sequence"].next_by_code("gll.trip.sequence")
    #     trips = super().create(vals_list)
    #     # Update trip_id in pickings
    #     for trip in trips:
    #         if trip.picking_ids:
    #             trip.picking_ids.write({"trip_ids": trip.ids})
    #     return trips

    # def write(self, vals):
    #     """Override write method to update trip_id in pickings"""
    #     result = super().write(vals)
    #     if 'picking_ids' in vals:
    #         for trip in self:
    #             # Get all pickings that were in this trip before the write
    #             old_pickings = self.env['stock.picking'].search([('trip_id', '=', trip.id)])
    #             # Get all pickings that are in this trip after the write
    #             current_pickings = trip.picking_ids
    #
    #             # Pickings that were removed from the trip
    #             removed_pickings = old_pickings - current_pickings
    #             if removed_pickings:
    #                 removed_pickings.write({'trip_id': False})
    #
    #             # Pickings that were added to the trip
    #             added_pickings = current_pickings - old_pickings
    #             if added_pickings:
    #                 added_pickings.write({'trip_id': trip.id})
    #     return result
