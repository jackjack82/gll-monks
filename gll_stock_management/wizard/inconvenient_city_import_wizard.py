# © 2025 webmonks

import base64
import re

import xlrd
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ExcelImportInconvenientWizard(models.Model):
    _name = "gll.excel.import.inconvenient.wizard"
    _description = "Excel Import Wizard for Inconvenient Places"

    name = fields.Char(compute="_compute_name", store=True)
    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Filename")
    carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Delivery Carrier",
        required=True,
        help="Delivery carrier to associate with the inconvenient places",
    )
    results = fields.Text(string="Result", readonly=True)
    country_id = fields.Many2one("res.country", "Country", required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("error", "Error")],
        string="State",
        default="draft",
    )

    @api.depends("filename")
    def _compute_name(self):
        for record in self:
            record.name = record.filename if record.filename else _("New Import")

    def action_import(self):
        """Import data from the uploaded Excel file"""

        self.ensure_one()

        if not self.file:
            raise UserError(_("No file uploaded."))

        if not self.filename or not self.filename.lower().endswith((".xlsx", ".xls")):
            raise UserError(_("Only Excel files (.xlsx, .xls) are supported."))

        try:
            # Decode the file content
            file_content = base64.b64decode(self.file)

            # Process the Excel file
            result_message = ""

            # Open the workbook
            book = xlrd.open_workbook(file_contents=file_content)
            sheet = book.sheet_by_index(0)

            # Validate header row (first row)
            if sheet.nrows < 2:  # At least header + 1 data row
                raise UserError(
                    _(
                        "The Excel file must contain at least a header row and one data row."
                    )
                )

            # Check column headers (must be in this order)
            expected_headers = ["name", "zip", "state"]
            actual_headers = [
                str(sheet.cell_value(0, i)).lower().strip()
                for i in range(min(4, sheet.ncols))
            ]
            if set(expected_headers) & set(actual_headers) != set(expected_headers):
                raise UserError(
                    _("Some expected header (name, zip, state) are missing")
                )

            if len(actual_headers) < 3:
                raise UserError(
                    _(
                        "The Excel file must contain at least 4 columns: nome, zip, provincia."
                    )
                )

            # Process data rows
            states_dict = {}
            for row_idx in range(1, sheet.nrows):
                try:
                    # Extract data from the row
                    row_dict = self._get_dict_from_row(sheet, row_idx, actual_headers)
                    state_id, states_dict = self._get_state_from_code(
                        row_dict["state"], states_dict
                    )
                    # Find or create city
                    city = self.env["res.city"].search(
                        [
                            ("name", "=", row_dict["name"]),
                            ("zipcode", "=", row_dict["zip"]),
                            # ("country_id", "=", self.country_id.id),
                            # ("state_id", "=", state_id.id)
                        ],
                        limit=1,
                    )

                    if not city:
                        city = self.env["res.city"].create(
                            {
                                "name": row_dict["name"],
                                "zipcode": row_dict["zip"],
                                "country_id": self.country_id.id,
                                "state_id": state_id.id,
                            }
                        )

                    # Add carrier to the city's inconvenient_place_ids
                    city.write({"inconvenient_place_ids": [(4, self.carrier_id.id)]})

                except Exception as e:
                    raise UserError(
                        "Error processing row {}: {}".format(row_idx + 1, str(e))
                    )

            # Update the wizard with results
            self.write(
                {
                    "state": "done",
                    "results": result_message,
                    # Store affected city IDs for later reference
                    # We could store this in a Many2many field if needed
                }
            )

            return True

        except Exception as e:
            self.write({"state": "error"})
            raise UserError(
                _("Import failed for the following reason: {}").format(str(e))
            )

    def _get_dict_from_row(self, sheet, row_idx, actual_headers):
        row_dict = {}
        for num, header in enumerate(actual_headers):
            value = str(sheet.cell_value(row_idx, num)).strip()
            if header == "zip":
                match = re.search(r"\b(\d{5})\b", value)
                value = str(match.group(1)) if match else False
            # check required fields, else raise an error
            if not value and header in ["name", "zip", "state"]:
                raise UserError(
                    _(
                        "The Excel file must contain at least 3 columns: name, zip, state"
                    )
                )
            row_dict[header] = value
        return row_dict

    def _get_state_from_code(self, code, states_dict):
        state_id = states_dict.get(code)
        if state_id:
            return state_id, states_dict
        state_id = self.env["res.country.state"].search(
            [
                ("code", "=", code),
            ],
            limit=1,
        )
        if not state_id:
            raise UserError(_("State '{}' not found.").format(code))
        states_dict[code] = state_id
        return state_id, states_dict
