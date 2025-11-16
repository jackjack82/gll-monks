import base64

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_type = fields.Selection(
        [
            ("deliveries", "Deliveries"),
            ("receipts", "Receipts"),
        ]
    )

    def _create_account_invoices(self, invoice_vals_list, final):
        """Override to automatically generate and attach reports to invoices."""
        # Create invoices using the standard method
        invoices = super()._create_account_invoices(invoice_vals_list, final)

        # Set period_from and period_to based on the invoice date
        for invoice in invoices:
            invoice.period_from = invoice.date
            invoice.period_to = invoice.date

        # Generate and attach the three reports for each invoice
        # for invoice in invoices:
        #     self._generate_and_attach_reports(invoice)

        return invoices

    def _generate_and_attach_reports(self, invoice):
        """Generate and attach the three reports to the invoice."""
        report_names = [
            "gll_stock_management.action_report_logistics_services_invoicing",
            "gll_stock_management.italy_transportation_services_report_action",
            "gll_stock_management.action_report_account_move_entrata_merci",
        ]

        for report_name in report_names:
            # Generate the report
            report = self.env.ref(report_name)
            report_content, report_format = report._render_qweb_pdf(
                report_name, invoice.id
            )

            # Determine the filename based on the report name
            if "logistics_services" in report_name:
                filename = f"Fatturazione_Servizi_Logistici_{invoice.name}.pdf"
            elif "trasporto_italia" in report_name:
                filename = f"Fatturazione_Servizi_Trasporto_Italia_{invoice.name}.pdf"
            else:
                filename = f"Consuntivo_entrata_merci_{invoice.name}.pdf"

            # Create the attachment
            attachment = self.env["ir.attachment"].create(
                {
                    "name": filename,
                    "type": "binary",
                    "datas": base64.b64encode(report_content),
                    "res_model": "account.move",
                    "res_id": invoice.id,
                    "mimetype": "application/pdf",
                }
            )

            # Link the attachment to the invoice
            invoice.message_post(
                body=f"Report {filename} automatically generated and attached",
                attachment_ids=[attachment.id],
            )
