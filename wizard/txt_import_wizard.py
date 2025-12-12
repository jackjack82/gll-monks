# © 2025 webmonks

import base64
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TxtImportWizard(models.Model):
    _name = "gll.txt.import.wizard"
    _description = "TXT Import Wizard"

    name = fields.Char(compute="_compute_name", store=True)
    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Filename")
    results = fields.Text(string="Result", readonly=True)
    picking_count = fields.Integer(
        compute="_compute_picking_count", string="Deliveries"
    )

    @api.depends("filename")
    def _compute_name(self):
        for record in self:
            record.name = record.filename if record.filename else _("New Import")

    def _compute_picking_count(self):
        for record in self:
            record.picking_count = self.env["stock.picking"].search_count(
                [("import_id", "=", record.id)]
            )

    def action_view_pickings(self):
        self.ensure_one()
        pickings = self.env["stock.picking"].search([("import_id", "=", self.id)])
        action = {
            "name": _("Deliveries"),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", pickings.ids)],
        }
        return action

    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("error", "Error")],
        string="State",
        default="draft",
    )

    def action_import(self):
        """Import data from the uploaded TXT file"""
        self.ensure_one()

        if not self.file:
            raise UserError(_("No file uploaded."))

        if not self.filename or not self.filename.lower().endswith(".txt"):
            raise UserError(_("Only .txt files are supported."))
        try:
            # Decode the file content
            file_content = base64.b64decode(self.file).decode("utf-8")
            lines = file_content.splitlines()

            # Process the file
            result_message = ""
            processed_pickings = {}
            file_line = 1

            for line in lines:
                if len(line) < 100:  # todo file finished with '\x1a'
                    continue

                # Extract data from the line based on positions
                try:
                    shipment_date_str = line[19:27].strip()

                    line_vals = {
                        "shipment_id": line[0:14].strip(),
                        "shipment_date_str": line[19:27].strip(),
                        "origin_doc": line[6:15].strip(),
                        "customer_name": line[86:120].strip(),
                        "customer_street": line[121:150].strip(),
                        "customer_zip": line[151:156].strip(),
                        "customer_state_code": line[156:158].strip(),
                        "customer_city": line[158:188].strip(),
                        "recipient_name": line[188:233].strip(),
                        "recipient_street": line[233:268].strip(),
                        "recipient_zip": line[268:275].strip(),
                        "recipient_state_code": line[276:278].strip(),
                        "recipient_city": line[278:308].strip(),
                        "delivery_note": line[309:411].strip(),
                        "product_ref": line[412:427].strip(),
                        "product_name": line[427:462].strip(),
                        "product_uom_code": line[462:464].strip(),
                        "product_qty": self.convert_to_int(line[464:473]),
                    }

                    # Convert date format
                    shipment_date = False
                    if shipment_date_str:
                        try:
                            shipment_date = datetime.strptime(
                                shipment_date_str, "%Y%m%d"
                            ).date()
                            line_vals["shipment_date"] = shipment_date
                        except ValueError:
                            result_message += f"\nWarning: Invalid date format for shipment {line_vals['shipment_id']}: {shipment_date_str}"

                    # Process the data
                    self._process_line(line_vals, processed_pickings, result_message)

                except Exception as e:
                    raise UserError(
                        _("Import suspended for the following reason: " + str(e))
                    )
                    # result_message += f"\nError processing line: {str(e)}"

            # Update the wizard with results
            self.write({"state": "done", "results": result_message})

            # Return the list of created pickings if successful
            if processed_pickings:
                picking_ids = list(processed_pickings.values())
                return {
                    "name": _("Created Deliveries"),
                    "type": "ir.actions.act_window",
                    "res_model": "stock.picking",
                    "view_mode": "list,form",
                    "domain": [("id", "in", [p.id for p in picking_ids])],
                }
            return True

        except Exception as e:
            # if there is any kind of error, rollback
            # self.env.cr.rollback()
            self.write({"state": "error"})
            raise UserError(_("Import failed for the following reason: " + str(e)))

    def _process_line(self, vals, processed_pickings, result_message):
        """Process a single line from the imported file"""
        shipment_id = vals["shipment_id"]
        # Check if we already processed this shipment
        if vals["shipment_id"] in processed_pickings:
            picking = processed_pickings[shipment_id]
            result_message += f"Adding product {vals['product_ref']} to existing picking {picking.name}"
        else:
            # Find or create the customer
            customer = self._find_or_create_partner(
                vals["customer_name"],
                vals["customer_street"],
                vals["customer_zip"],
                vals["customer_state_code"],
                vals["customer_city"],
                result_message,
            )

            # Find or create the recipient
            recipient = self._find_or_create_partner(
                vals["recipient_name"],
                vals["recipient_street"],
                vals["recipient_zip"],
                vals["recipient_state_code"],
                vals["recipient_city"],
                result_message,
            )

            # Create a new picking
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "outgoing")], limit=1
            )

            if not picking_type:
                raise UserError(_("No outgoing picking type found."))

            pick_vals = {
                "partner_id": recipient.id,
                "delivery_partner_id": customer.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": vals["origin_doc"],
                "scheduled_date": vals["shipment_date"],
                "import_id": self.id,
                "note": vals["delivery_note"],
            }

            picking = self.env["stock.picking"].create(pick_vals)
            processed_pickings[shipment_id] = picking
            result_message += (
                f"Created new picking {picking.name} for shipment {shipment_id}"
            )

        # Add the product to the picking
        self._add_product_to_picking(picking, result_message, vals)

        return picking

    def _find_or_create_partner(
        self, name, street, zip, state_code, city, result_message
    ):
        """Find or create a partner based on the provided information"""
        if not name:
            raise UserError(_("Partner name is required."))

        # Search for existing partner by name
        partner = self.env["res.partner"].search(
            [
                ("name", "=", name),
                ("parent_id", "=", False),
            ],
            limit=1,
        )
        if not partner:
            # create the main contact as a company
            partner = self.env["res.partner"].create(
                {"name": name, "company_type": "company"}
            )
            result_message += f"Created new partner: {name}"
        # manage the address as contact of the partner
        contact = partner.child_ids.filtered(
            lambda c: c.street == street and c.zip == zip
        )
        if contact:
            return contact
        # Find state based on code
        state = False
        if state_code:
            state = self.env["res.country.state"].search(
                [("code", "=", state_code)], limit=1
            )

        # Create new contact
        vals = {
            "name": "street",
            "company_type": "person",
            "type": "delivery",
            "parent_id": partner.id,
            "street": street,
            "zip": zip,
            "city": city,
        }

        if state:
            vals["state_id"] = state.id
            vals["country_id"] = state.country_id.id

        contact = self.env["res.partner"].create(vals)
        result_message += f"Created new contact for: {name}"

        return contact

    def _add_product_to_picking(self, picking, result_message, vals):
        """Add a product to the picking"""
        product_ref = vals["product_ref"]
        product_name = vals["product_name"]
        product_uom_code = vals["product_uom_code"]
        if not product_ref:
            result_message += "Warning: Empty product reference, skipping"
            return

        # Find the product
        product = self.env["product.product"].search(
            [("default_code", "=", product_ref)], limit=1
        )

        if not product:
            if product_name:
                # Find UoM by import code if provided
                uom_id = False
                if product_uom_code:
                    uom = self.env["uom.uom"].search(
                        [("import_code", "=", product_uom_code)], limit=1
                    )
                    if uom:
                        uom_id = uom.id
                        result_message += (
                            f"\nFound UoM with import code {product_uom_code}"
                        )
                    else:
                        raise UserError(
                            _(
                                f"\nWarning: UoM with import code {product_uom_code} not found."
                            )
                        )

                # Create a new product (storable with no tracking)
                product_vals = {
                    "name": product_name,
                    "default_code": product_ref,
                    "type": "consu",  # 'product' type means storable product
                    "is_storable": True,  # 'product' type means storable product
                    "tracking": "none",  # No tracking
                }

                # Set UoM if found
                if uom_id:
                    product_vals["uom_id"] = uom_id
                    product_vals["uom_po_id"] = uom_id

                product = self.env["product.product"].create(product_vals)
                result_message += (
                    f"Created new product {product_name} with reference {product_ref}"
                )
            else:
                result_message += (
                    f"Warning: Product with reference {product_ref} not found, skipping"
                )
                return

        # Create stock move
        move_vals = {
            "name": product.name,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": vals["product_qty"],
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
        }

        self.env["stock.move"].create(move_vals)
        result_message += f"Added product {product_ref} to picking {picking.name}"

    def convert_to_int(self, str_value):
        try:
            return int(str_value)
        except ValueError:
            return 0
