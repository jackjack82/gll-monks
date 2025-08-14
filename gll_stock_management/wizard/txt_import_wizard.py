# © 2025 webmonks

import base64
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TxtImportWizard(models.Model):
    _name = "gll.txt.import.wizard"
    _description = "TXT Import Wizard"

    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Filename")
    results = fields.Text(string="Result", readonly=True)
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("error", "Error")],
        string="State",
        default="draft",
        # readonly=True,
    )

    # @api.model
    # def create(self, vals):
    #     """Override create to ensure new records are in draft state"""
    #     if 'state' not in vals:
    #         vals['state'] = 'draft'
    #     return super(TxtImportWizard, self).create(vals)

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
                if len(line) < 100: # todo file finished with '\x1a'
                    continue

                # Extract data from the line based on positions
                try:
                    shipment_id = line[0:14].strip()
                    shipment_date_str = line[19:27].strip()
                    origin_doc = line[28:77].strip()  # todo: togliere zeri?
                    customer_name = line[86:120].strip()
                    customer_street = line[121:150].strip()  # TODO: è 124R ?
                    customer_zip = line[151:156].strip()
                    customer_state_code = line[156:158].strip()
                    customer_city = line[158:188].strip()
                    recipient_name = line[188:233].strip()
                    recipient_street = line[233:268].strip()
                    recipient_zip = line[268:275].strip()
                    recipient_state_code = line[276:278].strip()
                    recipient_city = line[278:308].strip()
                    delivery_note = line[309:426].strip()
                    product_ref = line[412:427].strip()
                    product_name = line[427:462].strip()

                    # Convert date format
                    shipment_date = False
                    if shipment_date_str:
                        try:
                            shipment_date = datetime.strptime(
                                shipment_date_str, "%Y%m%d"
                            ).date()
                        except ValueError:
                            result_message += f"\nWarning: Invalid date format for shipment {shipment_id}: {shipment_date_str}"

                    # Process the data
                    self._process_line(
                        shipment_id,
                        shipment_date,
                        origin_doc,
                        customer_name,
                        customer_street,
                        customer_zip,
                        customer_state_code,
                        customer_city,
                        recipient_name,
                        recipient_street,
                        recipient_zip,
                        recipient_state_code,
                        recipient_city,
                        product_ref,
                        processed_pickings,
                        result_message,
                        delivery_note,
                        product_name,
                    )

                except Exception as e:
                    result_message += f"\nError processing line: {str(e)}"

            # Update the wizard with results
            self.write({"state": "done", "results": result_message})

        except Exception as e:
            self.write({"state": "error", "error": str(e)})

    def _process_line(
        self,
        shipment_id,
        shipment_date,
        origin_doc,
        customer_name,
        customer_street,
        customer_zip,
        customer_state_code,
        customer_city,
        recipient_name,
        recipient_street,
        recipient_zip,
        recipient_state_code,
        recipient_city,
        product_ref,
        processed_pickings,
        result_message,
        delivery_note,
        product_name,
    ):
        """Process a single line from the imported file"""

        # Check if we already processed this shipment
        if shipment_id in processed_pickings:
            picking = processed_pickings[shipment_id]
            result_message += (
                f"Adding product {product_ref} to existing picking {picking.name}"
            )
        else:
            # Find or create the customer
            customer = self._find_or_create_partner(
                customer_name,
                customer_street,
                customer_zip,
                customer_state_code,
                customer_city,
                result_message,
            )

            # Find or create the recipient
            recipient = self._find_or_create_partner(
                recipient_name,
                recipient_street,
                recipient_zip,
                recipient_state_code,
                recipient_city,
                result_message,
            )

            # Create a new picking
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "outgoing")], limit=1
            )

            if not picking_type:
                raise UserError(_("No outgoing picking type found."))

            vals = {
                "partner_id": recipient.id,
                "delivery_partner_id": customer.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": origin_doc,
                "scheduled_date": shipment_date,
                "import_id": self.id,
                "note": delivery_note,
            }

            picking = self.env["stock.picking"].create(vals)
            processed_pickings[shipment_id] = picking
            result_message += (
                f"Created new picking {picking.name} for shipment {shipment_id}"
            )

        # Add the product to the picking
        self._add_product_to_picking(picking, product_ref, result_message)

        return picking

    def _find_or_create_partner(
        self, name, street, zip_code, state_code, city, result_message
    ):
        """Find or create a partner based on the provided information"""
        if not name:
            raise UserError(_("Partner name is required."))

        # Search for existing partner by name
        partner = self.env["res.partner"].search([("name", "=", name)], limit=1)

        if not partner:
            # Find state based on code
            state = False
            if state_code:
                state = self.env["res.country.state"].search(
                    [("code", "=", state_code)], limit=1
                )

            # Create new partner
            vals = {
                "name": name,
                "street": street,
                "zip": zip_code,
                "city": city,
            }

            if state:
                vals["state_id"] = state.id
                vals["country_id"] = state.country_id.id

            partner = self.env["res.partner"].create(vals)
            result_message += f"Created new partner: {name}"

        return partner

    def _add_product_to_picking(self, picking, product_ref, result_message):
        """Add a product to the picking"""
        if not product_ref:
            result_message += "Warning: Empty product reference, skipping"
            return

        # Find the product
        product = self.env["product.product"].search(
            [("default_code", "=", product_ref)], limit=1
        )

        if not product:
            result_message += (
                f"Warning: Product with reference {product_ref} not found, skipping"
            )
            return

        # Create stock move
        move_vals = {
            "name": product.name,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": 1.0,  # Default quantity as per requirements
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
        }

        self.env["stock.move"].create(move_vals)
        result_message += f"Added product {product_ref} to picking {picking.name}"
