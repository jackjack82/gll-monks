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
            sale_orders = invoice._get_sale_orders_from_invoice()

            # Get relevant pickings
            pickings = invoice._get_pickings_from_sale_orders(sale_orders)

            # Prepare data for each picking
            picking_data = []

            for picking in pickings:
                preparation_amount = picking._get_preparation_amount()
                fixed_amount = picking._get_fixed_amount()
                logistics_amount = picking._get_logistics_amount()

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
