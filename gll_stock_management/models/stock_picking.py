from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Partner",
    )

    service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Services",
    )

    fixed_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Fixed Services",
        domain=[("service_type", "=", "fixed")],
    )

    variable_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Variable Services",
        domain=[("service_type", "=", "variable")],
    )

    fixed_total = fields.Float(
        string="Fixed Services Total",
        compute="_compute_service_totals",
        store=True,
    )

    variable_total = fields.Float(
        string="Variable Services Total",
        compute="_compute_service_totals",
        store=True,
    )
    import_id = fields.Many2one(
        "gll.txt.import.wizard",
        string="Import Reference",
        readonly=True,
    )
    trip_id = fields.Many2one(
        "gll.trip",
        string="Trip",
        tracking=True,
    )
    # Related partner fields
    partner_street = fields.Char(
        related="partner_id.street",
        string="Street",
        store=True,
        readonly=False,
    )
    partner_zip = fields.Char(
        related="partner_id.zip",
        string="ZIP",
        store=True,
        readonly=False,
    )
    partner_city = fields.Char(
        related="partner_id.city",
        string="City",
        store=True,
        readonly=False,
    )
    partner_country_id = fields.Many2one(
        related="partner_id.country_id",
        string="Country",
        store=True,
        readonly=False,
    )
    items_count = fields.Integer(
        compute="compute_items_count_volume",
        store=True,
        string="Number of items",
    )
    packages_count = fields.Integer(
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
            lines = self.move_ids.move_line_ids
            picking.items_volume = sum(
                sml.quantity * sml.product_id.volume for sml in lines
            )
            picking.items_count = sum(sml.quantity for sml in lines)
            picking.packages_count = len(lines.result_package_id)

    @api.depends("service_ids.total", "service_ids.service_type")
    def _compute_service_totals(self):
        for picking in self:
            picking.fixed_total = sum(
                service.total
                for service in picking.service_ids.filtered(
                    lambda s: s.service_type == "fixed"
                )
            )
            picking.variable_total = sum(
                service.total
                for service in picking.service_ids.filtered(
                    lambda s: s.service_type == "variable"
                )
            )

    def button_validate(self):
        """At validation, trigger again packages and items computation"""
        for picking in self:
            if not all(
                pack.package_type_id for pack in picking.move_line_ids.result_package_id
            ):
                raise UserError(
                    _("Please set a package type for all packages before validation.")
                )
            picking.compute_items_count_volume()

        res = super(StockPicking, self).button_validate()
        for picking in self:
            if not picking.origin:
                picking.origin = picking.name
        return res

    def action_create_trip(self):
        """Create a new trip from selected pickings"""
        # Check if any pickings are selected
        if not self:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Deliveries Selected",
                    "message": "Please select at least one delivery to create a trip.",
                    "sticky": False,
                    "type": "warning",
                },
            }

        # Get the common partner if possible
        partners = self.mapped("partner_id")
        common_partner = partners[0] if len(partners) == 1 else False

        # Create a new trip
        trip = self.env["gll.trip"].create(
            {
                "name": f"Trip {fields.Date.today()}",
                "partner_id": common_partner.id
                if common_partner
                else self.env.company.partner_id.id,
            }
        )

        # Associate the pickings with the trip
        self.write({"trip_id": trip.id})

        # Return an action to open the new trip
        return {
            "name": "New Trip",
            "type": "ir.actions.act_window",
            "res_model": "gll.trip",
            "view_mode": "form",
            "res_id": trip.id,
            "target": "current",
        }

    def create_sale_order_packages(self, operation_type):
        """Create a SO with partner the delivery address of the picking.
        SO lines should include, depending on the TYPE:
            1) 'receipt': all the products related to the packages
                used in the receipts.
            2) 'deliveries': all the products related to the packages used
                for deliveries to
        """
        # selecting the proper transfer depending on the operation type
        if operation_type == "receipts":
            pickings = self.filtered(lambda pick: pick.picking_type_code == "incoming")
        elif operation_type == "deliveries":
            pickings = self.filtered(lambda pick: pick.picking_type_code == "outgoing")
        else:
            raise UserError(_("Operation type not defined."))

        if not pickings:
            msg_type = "Deliveries" if operation_type == "delivery" else "Receipts"
            raise UserError(_(f"No {msg_type} found for the selected transfers."))

        # grouping by receipts or delivery partner
        partner_ids = pickings.mapped("partner_id")
        sale_orders = self.env["sale.order"]

        for partner_id in partner_ids:
            picks = pickings.filtered(lambda p: p.partner_id == partner_id)
            packages = picks.move_line_ids.mapped("result_package_id")
            # if not packages: TODO: decide how to raise errors, now skip this edge case
            #     raise UserError(_("No packages found for the selected transfer."))

            if not all([pick.state == "done" for pick in picks]):
                raise UserError(
                    _("All transfers have to be validated for this operation.")
                )

            # Count packages by package type
            package_type_counts = {}
            for package in packages:
                package_type = package.package_type_id
                if not package_type:
                    raise UserError(
                        _(f"No package type found for package {package.name}.")
                    )
                if package_type not in package_type_counts:
                    package_type_counts[package_type] = 0
                package_type_counts[package_type] += 1

            if not package_type_counts:
                raise UserError(
                    _("No package types found for the packages in the transfer.")
                )

            # Create sale orders for each package type
            order_lines = []
            for package_type, count in package_type_counts.items():
                # Check if package type has products
                product = package_type.get_order_product_id(operation_type)
                if not product:
                    raise UserError(
                        _(f"No products found for the package type {package_type.name}")
                    )
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": count,
                            "price_unit": product.list_price,
                        },
                    )
                )

            sale_orders |= self.env["sale.order"].create(
                {
                    "partner_id": partner_id.id,
                    "order_line": order_lines,
                    "origin": ",".join([pick.name for pick in picks]),
                }
            )

        # Return action to view created sale orders
        action = {
            "name": _("Sale Orders"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", sale_orders.ids)],
            "target": "current",
        }

        return action
