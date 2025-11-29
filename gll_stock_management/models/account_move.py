# © 2025 webmonks

from odoo import api, fields, models

from .product import SERVICE_TYPE


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    service_type = fields.Selection(SERVICE_TYPE)

    @api.model_create_multi
    def create(self, vals):
        if not vals:
            return super().create(vals)
        for line in vals:
            product = line.get("product_id")
            if product:
                product = self.env["product.product"].browse(product)
                line["service_type"] = (
                    product.pick_service_type
                    or product.product_tmpl_id.pick_service_type
                )
        return super().create(vals)


class AccountMove(models.Model):
    _inherit = "account.move"

    # Period fields
    period_from = fields.Date(
        string="Period From",
        help="Start date of the period covered by this invoice",
    )
    period_to = fields.Date(
        string="Period To",
        help="End date of the period covered by this invoice",
    )

    # Logistics Services fields
    logistics_services = fields.Float(
        string="Servizi Logistici",
        compute="_compute_services_totals",
        store=True,
        help="Sum of all move lines with products of type warehouse",
    )
    fixed_fee = fields.Float(
        string="Diritto Fisso",
        compute="_compute_services_totals",
        store=True,
        help="Sum of all move lines with products of type subscription",
    )
    preparation = fields.Float(
        string="Preparazione",
        compute="_compute_services_totals",
        store=True,
        help="Sum of all move lines with products linked to the configuration parameters",
    )
    logistics_total = fields.Float(
        string="Totale Logistico",
        compute="_compute_services_totals",
        store=True,
        help="Sum of the three fields: Logistics Services + Fixed Fee + Preparation",
    )

    # Transport Services Italy fields
    transport_total = fields.Float(
        string="Servizi Trasporto",
        compute="_compute_services_totals",
        store=True,
    )
    accessories_total = fields.Float(
        string="Accessories",
        compute="_compute_services_totals",
        store=True,
    )
    additional_total = fields.Float(
        string="Additional",
        compute="_compute_services_totals",
        store=True,
    )
    fixed_total = fields.Float(
        string="Fixed",
        compute="_compute_services_totals",
        store=True,
    )
    variable_total = fields.Float(
        string="Variable",
        compute="_compute_services_totals",
        store=True,
    )
    total_transport = fields.Float(
        string="Total Transport",
        compute="_compute_services_totals",
        store=True,
        help="Sum of all calculated values in this group",
    )

    # Other Services fields
    other_services = fields.Float(
        string="Other Services",
        compute="_compute_services_totals",
        store=True,
        help="Sum of all move lines not included in the previous groups",
    )
    total_other_services = fields.Float(
        string="Total Other Services",
        compute="_compute_services_totals",
        store=True,
        help="Sum of these lines",
    )

    @api.depends("invoice_line_ids.service_type", "invoice_line_ids.price_subtotal")
    def _compute_services_totals(self):
        """Compute the fields for the all services."""
        for move in self:
            # Servizi logistici: sum of move lines with products having pick_service_type = 'warehouse'
            move.logistics_services = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.product_id.warehouse_type == "logistic"
            )

            # Diritto fisso: sum of move lines with products having pick_service_type = 'subscription'
            move.fixed_fee = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.product_id.warehouse_type == "fix"
            )

            # Preparazione: sum of move lines with products linked to service_for_box_id and service_for_single_id
            move.preparation = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.product_id.warehouse_type == "preparation"
            )
            # sp_obj = self.env["stock.picking"]
            # (
            #     service_for_single_id,
            #     service_for_box_id,
            # ) = sp_obj.get_single_box_product_services()
            # move.preparation = sum(
            #     service.price_subtotal
            #     for service in move.invoice_line_ids
            #     if service.product_id.id in [service_for_single_id, service_for_box_id]
            # )

            # Totale logistico: sum of the above three fields
            move.logistics_total = (
                move.logistics_services + move.fixed_fee + move.preparation
            )

            ### transportation services ###
            # Sum for each pick_service_type different from 'warehouse' and 'subscription'

            move.transport_total = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.service_type == "transport"
            )

            move.accessories_total = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.service_type == "accessories"
            )

            move.additional_total = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.service_type == "additional"
            )

            move.fixed_total = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.service_type == "fixed"
            )

            move.variable_total = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.service_type == "variable"
            )

            # Totale trasporto: sum of all values in this group
            move.total_transport = (
                move.transport_total
                + move.accessories_total
                + move.additional_total
                + move.fixed_total
                + move.variable_total
            )

            ### OTHER SERVICES ###
            # Altri servizi: sum of all move lines not included in the previous groups
            # (products without any specified pick_service_type)
            move.other_services = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if not service.service_type
            )

            # Totale altri servizi: sum of these lines
            move.total_other_services = move.other_services

    def get_logistic_services_report_data(self):
        """Picking data collection method for 'Servizi logistici'
        report."""
        self._compute_services_totals()
        # Get relevant sale orders
        sale_orders = self._get_sale_orders_from_invoice()
        pickings = self._get_pickings_from_sale_orders(sale_orders)

        # # Prepare data for each picking
        outgoing_data = []
        incoming_data = []
        preparation_total = 0.0
        fixed_total = 0.0
        logistics_total = 0.0

        for picking in pickings:
            additional_services = picking.all_service_ids.filtered(
                lambda s: s.pick_service_type == "additional"
            )
            additional_total = sum(s.total for s in additional_services)
            preparation_amount = picking._get_preparation_amount()
            fixed_amount = picking._get_fixed_amount()
            logistics_amount = picking._get_logistics_amount()
            total_amount = (
                preparation_amount + fixed_amount + logistics_amount + additional_total
            )

            preparation_total += preparation_amount
            fixed_total += fixed_amount
            logistics_total += logistics_amount

            vals = {
                "picking": picking,
                "name": picking.origin,
                "date_done": picking.date_done,
                "partner_id": picking.partner_id,
                "packages_count": picking.packages_count,
                "weight": picking.weight,
                "preparation_amount": preparation_amount,
                "fixed_amount": fixed_amount,
                "logistics_amount": logistics_amount,
                "additional_services": additional_services,
                "total_amount": total_amount,
            }
            if picking.picking_type_code == "outgoing":
                outgoing_data.append(vals)
            else:
                incoming_data.append(vals)
        return {
            "docs": self,
            "outgoing_data": outgoing_data,
            "incoming_data": incoming_data,
            "preparation_total": preparation_total,
            "fixed_total": fixed_total,
            "logistics_total": logistics_total,
            "num_documents": len(pickings),
        }

    def _get_sale_orders_from_invoice(self):
        """Get the relevant sale orders from an invoice."""
        # Get sale orders linked to the invoice through its lines
        sale_line_ids = self.invoice_line_ids.mapped("sale_line_ids")
        sale_orders = sale_line_ids.mapped("order_id")

        # Filter by order_type and state
        return sale_orders.filtered(lambda o: o.state in ["sale", "done"])

    def _get_pickings_from_sale_orders(self, sale_orders):
        """Get the relevant pickings from sale orders."""
        # Get all sale order lines
        sale_lines = sale_orders.mapped("order_line")

        # Get pickings that have services linked to these sale order lines
        pickings = self.env["stock.picking"].search(
            [
                ("picking_type_code", "in", ["incoming", "outgoing"]),
                ("state", "in", ["done"]),
                ("all_service_ids.sale_line_id", "in", sale_lines.ids),
            ]
        )

        return pickings

    def get_italy_transportation_report_data(self):
        """Picking data collection method for 'Servizi logistici'
        report."""
        self._compute_services_totals()
        # Get relevant sale orders
        sale_orders = self._get_sale_orders_from_invoice()
        pickings = self._get_pickings_from_sale_orders(sale_orders)

        # # Prepare data for each picking
        incoming_data = []
        total_prod_dict = {}

        for picking in pickings:
            # TODO: filter only the lines related to this invoice
            # creating a dictionary with the total of all products
            for service in picking.all_service_ids:
                if not total_prod_dict.get(service.product_id):
                    total_prod_dict[service] = service.total
                else:
                    total_prod_dict[service] += service.total
            vals = {
                "picking": picking,
                "name": picking.origin,
                "date_done": picking.date_done,
                "partner_id": picking.partner_id,
                "packages_count": picking.packages_count,
                "weight": picking.weight
            }
            incoming_data.append(vals)

        return {
            "docs": self,
            "incoming_data": incoming_data,
            "num_documents": len(pickings),
            "total_prod_dict": total_prod_dict,
        }