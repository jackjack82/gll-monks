from odoo import _, api, fields, models
from odoo.exceptions import UserError

SERVICE_TYPE = [
    ("warehouse", "Warehouse"),
    ("transport", "Transport"),
    ("accessories", "Accessories"),
    ("additional", "Additional"),
    ("fixed", "Fixed"),
    ("variable", "Variable"),
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals):
        # Create the picking first
        picking = super(StockPicking, self).create(vals)

        # Only proceed for incoming and outgoing pickings
        if picking.picking_type_code in ["incoming", "outgoing"]:
            for service, _ in SERVICE_TYPE:
                # Find fixed service products
                fixed_products = self.env["product.product"].search(
                    [("product_tmpl_id.pick_service_type", "=", service)]
                )

                # Create fixed services for both incoming and outgoing
                for product in fixed_products:
                    self.env["picking.service"].create(
                        {
                            "picking_id": picking.id,
                            "product_id": product.id,
                            "pick_service_type": service,
                            "quantity": 0.0,
                            "price": 0.0,
                        }
                    )

            # For outgoing pickings, also add variable services
            if picking.picking_type_code == "outgoing":
                variable_products = self.env["product.product"].search(
                    [("product_tmpl_id.pick_service_type", "=", "variable")]
                )

                for product in variable_products:
                    self.env["picking.service"].create(
                        {
                            "picking_id": picking.id,
                            "product_id": product.id,
                            "pick_service_type": "variable",
                            "quantity": 0.0,
                            "price": 0.0,
                        }
                    )

        return picking

    delivery_partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Partner",
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

    # all service fields plus their computed total
    warehouse_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Warehouse Services",
        domain=[("pick_service_type", "=", "warehouse")],
    )
    warehouse_total = fields.Float(
        string="Warehouse Services Total",
        compute="_compute_service_totals",
        store=True,
    )
    transport_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Transport Services",
        domain=[("pick_service_type", "=", "transport")],
    )
    transport_total = fields.Float(
        string="Transport Services Total",
        compute="_compute_service_totals",
        store=True,
    )
    accessories_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Accessories Services",
        domain=[("pick_service_type", "=", "accessories")],
    )
    accessories_total = fields.Float(
        string="Accessories Services Total",
        compute="_compute_service_totals",
        store=True,
    )
    additional_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Additional Services",
        domain=[("pick_service_type", "=", "additional")],
    )
    additional_total = fields.Float(
        string="Additional Services Total",
        compute="_compute_service_totals",
        store=True,
    )
    fixed_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Fixed Services",
        domain=[("pick_service_type", "=", "fixed")],
    )
    fixed_total = fields.Float(
        string="Fixed Services Total",
        compute="_compute_service_totals",
        store=True,
    )

    variable_service_ids = fields.One2many(
        "picking.service",
        "picking_id",
        string="Variable Services",
        domain=[("pick_service_type", "=", "variable")],
    )
    variable_total = fields.Float(
        string="Variable Services Total",
        compute="_compute_service_totals",
        store=True,
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

    @api.depends("fixed_service_ids.total", "variable_service_ids.total")
    def _compute_service_totals(self):
        for picking in self:
            picking.fixed_total = sum(
                service.total for service in picking.fixed_service_ids
            )
            picking.variable_total = sum(
                service.total for service in picking.variable_service_ids
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
        # checking the pick status and raise an error
        unconfirmed_pick = self.filtered(lambda pick: pick.state != "done")
        if unconfirmed_pick:
            raise UserError(_("You can call this action only on confirmed transfers."))
        # selecting the proper transfer depending on the operation type
        if operation_type == "receipts":
            self.create_sale_order_receipts()
        elif operation_type == "deliveries":
            self.create_sale_order_deliveries()
        else:
            raise UserError(_("Invalid operation type"))

    def create_sale_order_deliveries(self):
        """Create a SO with services related to receipt."""
        wrong_type = self.filtered(lambda pick: pick.picking_type_code != "incoming")
        if wrong_type:
            raise UserError(_("You can call this feature only for incoming pickings."))

    def create_sale_order_receipts(self):
        """Create a SO"""
        wrong_type = self.filtered(lambda pick: pick.picking_type_code != "incoming")
        if wrong_type:
            raise UserError(_("You can call this feature only for incoming pickings."))
        if not self:
            raise UserError(_(f"No deliveries found for the selected transfers."))
        # if len(self) > 1:
        #     raise UserError(_("You can create Sale Orders only for one transfer at the time."))

        # grouping by receipts or delivery partner
        partner_ids = self.mapped("partner_id")
        sale_orders = self.env["sale.order"]

        for partner_id in partner_ids:
            picks = self.filtered(lambda p: p.partner_id == partner_id)
            # if not packages: TODO: decide how to raise errors, now skip this edge case
            #     raise UserError(_("No packages found for the selected transfer."))

            if not all([pick.state == "done" for pick in picks]):
                raise UserError(
                    _("All transfers have to be validated for this operation.")
                )
            # get config products for single and box products
            (
                service_for_single_id,
                service_for_box_id,
            ) = self.get_single_box_product_services()

            single_products = sum(
                line.product_uom_qty
                for line in picks.move_ids
                if line.product_id.package_type == "single"
            )
            box_products = sum(
                line.product_uom_qty
                for line in picks.move_ids
                if line.product_id.package_type == "box"
            )

            # Create sale orders for each package type
            order_line_tuples = [
                (service_for_single_id, single_products),
                (service_for_box_id, box_products),
            ]
            order_lines = []
            for prod_id, count in order_line_tuples:
                product = self.env["product.product"].browse(prod_id)
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

            # add fixed and variable services for DELIVERIES
            for line in picks.variable_service_ids + picks.fixed_service_ids:
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.quantity,
                            "price_unit": line.price,
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

    def get_single_box_product_services(self):
        # get products
        icp_obj = self.env["ir.config_parameter"].sudo()
        service_for_box_id = icp_obj.get_param(
            "gll_stock_management.service_for_box_id"
        )
        if not service_for_box_id:
            raise UserError(
                _("You need to specify the service you wish to use for box products.")
            )

        service_for_single_id = icp_obj.get_param(
            "gll_stock_management.service_for_single_id"
        )
        if not service_for_single_id:
            raise UserError(
                _(
                    "You need to specify the service you wish to use for single products."
                )
            )

        return int(service_for_single_id), int(service_for_box_id)
