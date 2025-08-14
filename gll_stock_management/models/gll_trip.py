# © 2025 webmonks

from odoo import api, fields, models


class GllTrip(models.Model):
    _name = "gll.trip"
    _description = "Trip"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        tracking=True,
    )
    note = fields.Text(string="Notes", tracking=True)
    picking_ids = fields.One2many(
        "stock.picking",
        "trip_id",
        string="Deliveries",
    )
    picking_count = fields.Integer(
        string="Delivery Count",
        compute="_compute_picking_count",
        store=True,
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
            "view_mode": "tree,form",
            "domain": [("id", "in", self.picking_ids.ids)],
        }
        return action
