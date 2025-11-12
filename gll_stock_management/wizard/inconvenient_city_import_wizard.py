# © 2025 webmonks

import base64
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
    country_id = fields.Many2one('res.country', "Country", required=True)
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
            affected_cities = []
            
            # Open the workbook
            book = xlrd.open_workbook(file_contents=file_content)
            sheet = book.sheet_by_index(0)
            
            # Validate header row (first row)
            if sheet.nrows < 2:  # At least header + 1 data row
                raise UserError(_("The Excel file must contain at least a header row and one data row."))
            
            # Check column headers (must be in this order)
            expected_headers = ["name", "zip", "state"]
            actual_headers = [str(sheet.cell_value(0, i)).lower().strip() for i in range(min(4, sheet.ncols))]
            
            if len(actual_headers) < 3:
                raise UserError(_("The Excel file must contain at least 4 columns: nome, zip, provincia."))

            # Process data rows
            for row_idx in range(1, sheet.nrows):
                try:
                    # Extract data from the row
                    name = str(sheet.cell_value(row_idx, 0)).strip()
                    zipcode = str(sheet.cell_value(row_idx, 1)).strip()
                    country_code = str(sheet.cell_value(row_idx, 2)).strip()
                    state_code = str(sheet.cell_value(row_idx, 3)).strip()
                    
                    # Validate required fields
                    if not name or not zipcode:
                        result_message += _("\nWarning: Row {} has empty name or zip, skipping.").format(row_idx + 1)
                        continue
                    
                    # Find country by code or name
                    country = self.env["res.country"].search([
                        "|",
                        ("code", "=ilike", country_code),
                        ("name", "=ilike", country_code)
                    ], limit=1)
                    
                    if not country:
                        raise UserError(_("Country '{}' not found in row {}.").format(country_code, row_idx + 1))
                    
                    # Find state by code or name, ensuring it belongs to the country
                    state = self.env["res.country.state"].search([
                        "|",
                        ("code", "=ilike", state_code),
                        ("name", "=ilike", state_code),
                        ("country_id", "=", country.id)
                    ], limit=1)
                    
                    if not state:
                        raise UserError(_("State '{}' not found for country '{}' in row {}.").format(
                            state_code, country.name, row_idx + 1))
                    
                    # Find or create city
                    city = self.env["res.city"].search([
                        ("name", "=ilike", name),
                        ("zipcode", "=", zipcode),
                        ("country_id", "=", country.id),
                        ("state_id", "=", state.id)
                    ], limit=1)
                    
                    if city:
                        result_message += _("\nUpdated existing city {} {} ({}-{})").format(
                            city.name, city.zipcode, country.code, state.code)
                    else:
                        city = self.env["res.city"].create({
                            "name": name,
                            "zipcode": zipcode,
                            "country_id": country.id,
                            "state_id": state.id
                        })
                        result_message += _("\nCreated city {} {} ({}-{})").format(
                            city.name, city.zipcode, country.code, state.code)
                    
                    # Add carrier to the city's inconvenient_place_ids
                    if self.carrier_id.id not in city.inconvenient_place_ids.ids:
                        city.write({
                            "inconvenient_place_ids": [(4, self.carrier_id.id)]
                        })
                        result_message += _("\nAssociated carrier {} to city {} {}").format(
                            self.carrier_id.name, city.name, city.zipcode)
                    
                    affected_cities.append(city.id)
                
                except Exception as e:
                    result_message += _("\nError processing row {}: {}").format(row_idx + 1, str(e))
            
            # Update the wizard with results
            self.write({
                "state": "done",
                "results": result_message,
                # Store affected city IDs for later reference
                # We could store this in a Many2many field if needed
            })
            
            return True
        
        except Exception as e:
            self.write({"state": "error"})
            raise UserError(_("Import failed for the following reason: {}").format(str(e)))