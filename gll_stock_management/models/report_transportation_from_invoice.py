"""
Report parser for the Transportation Services from Invoice report.
"""
from odoo import api, fields, models


class ReportItalyTransportationServicesFromInvoice(models.AbstractModel):
    _name = "report.gll_stock_management.report_transportation_from_invoice"
    _description = "Transportation Services from Invoice Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Prepare the data for the report.

        Args:
            docids: The IDs of the documents to report on.
            data: Additional data.

        Returns:
            dict: The data for the report.
        """
        if not docids:
            return {}

        invoices = self.env["account.move"].browse(docids)
        result = []
        preparation_total = 0.0
        fixed_total = 0.0
        logistics_total = 0.0

        for invoice in invoices:
            # Get relevant sale orders
            sale_orders = self._get_sale_orders_from_invoice(invoice)

            # Get relevant pickings
            pickings = self._get_pickings_from_sale_orders(sale_orders)

            # Prepare data for each picking
            picking_data = []

            for picking in pickings:
                preparation_amount = self._get_preparation_amount(picking)
                fixed_amount = self._get_fixed_amount(picking)
                logistics_amount = self._get_logistics_amount(picking)

                preparation_total += preparation_amount
                fixed_total += fixed_amount
                logistics_total += logistics_amount

                picking_data.append(
                    {
                        "picking": picking,
                        "name": picking.origin,
                        "date_done": picking.date_done,
                        "partner_id": picking.partner_id,
                        "packages_count": picking.packages_count,
                        "weight": picking.weight,
                        "preparation_amount": preparation_amount,
                        "fixed_amount": fixed_amount,
                        "logistics_amount": logistics_amount,
                    }
                )

            result.append(
                {
                    "invoice": invoice,
                    "pickings": picking_data,
                }
            )

        return {
            "docs": invoices,
            "data": result,
            "preparation_total": preparation_total,
            "fixed_total": fixed_total,
            "logistics_total": logistics_total,
        }

    def _get_preparation_amount(self, picking):
        """
        Calculate the preparation amount for a picking.
        Sum the total of all warehouse services with warehouse_type = 'preparation'.
        """
        preparation_services = picking.warehouse_service_ids.filtered(
            lambda s: s.product_id.warehouse_type == "preparation" and s.quantity
        )
        return sum(service.total for service in preparation_services)

    def _get_fixed_amount(self, picking):
        """
        Calculate the fixed amount for a picking.
        Sum the total of all warehouse services with warehouse_type = 'fix'.
        """
        fixed_services = picking.warehouse_service_ids.filtered(
            lambda s: s.product_id.warehouse_type == "fix" and s.quantity
        )
        return sum(service.total for service in fixed_services)

    def _get_logistics_amount(self, picking):
        """
        Calculate the logistics amount for a picking.
        Sum the total of all warehouse services with warehouse_type = 'logistic'.
        """
        logistics_services = picking.warehouse_service_ids.filtered(
            lambda s: s.product_id.warehouse_type == "logistic" and s.quantity
        )
        return sum(service.total for service in logistics_services)
