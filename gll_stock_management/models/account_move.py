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
                if service.service_type == "warehouse"
            )

            # Diritto fisso: sum of move lines with products having pick_service_type = 'subscription'
            move.fixed_fee = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.service_type == "subscription"
            )

            # Preparazione: sum of move lines with products linked to service_for_box_id and service_for_single_id
            sp_obj = self.env["stock.picking"]
            (
                service_for_single_id,
                service_for_box_id,
            ) = sp_obj.get_single_box_product_services()
            move.preparation = sum(
                service.price_subtotal
                for service in move.invoice_line_ids
                if service.product_id.id in [service_for_single_id, service_for_box_id]
            )

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
