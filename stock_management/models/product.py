# © 2021 bloopark systems (<http://bloopark.de>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    barcode = fields.Char(string="EAN")
    intrastat_code_id = fields.Many2one(string="HS Code ")


class ProductProduct(models.Model):
    _inherit = "product.product"

    barcode = fields.Char(string="EAN")
    default_code = fields.Char(tracking=True)
    intrastat_code_id = fields.Many2one(string="HS Code ")
    package_type_ids = fields.One2many("stock.package.type", "product_id")

    def get_possible_dep_ids(self, dep_customer, customer_id=False):
        """This method returns the DEP that are allowed to select
        for a given DEP (usually in SO). This method shall be used to check
        a certain product availability for a given DEP customer."""
        if dep_customer:
            dep_types = self.process_dep_ids_utilising_mdm(dep_customer, customer_id)
            if not dep_types:
                return dep_customer.allowed_dep_ids.ids
            return dep_types
        else:
            return self.get_no_customer_dep_ids() + [False]

    def get_no_customer_dep_ids(self):
        """Method to get DEP IDs for no customer"""
        domain = [("dep_type", "in", ["is_stock", "no_dep"])]
        return self.env["dep.customer"].search(domain).ids

    def get_dep_ids_by_type(self, dep_customer_type):
        """Method to get DEP IDs by type"""
        domain = [("dep_type", "=", dep_customer_type)]
        return self.env["dep.customer"].search(domain).ids

    def invalid_mdm_configurations(self, customer_id):
        """Check if the MDM data is invalid for the given customer."""
        invalid_fields = {"disable_utilising_mdm_logic": False, "mdm_data": False}

        # Check system parameter to see if the availability
        # utilising MDM logic is disabled
        disable_utilising_mdm_logic = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("disable_availability_utilising_mdm_logic")
        )
        if disable_utilising_mdm_logic == 1:
            invalid_fields["disable_utilising_mdm_logic"] = True

        valid_mdm_values = ("true", "false")
        mdm_enrolment_access = customer_id.enrolment_access
        mdm_enrolment_permission = customer_id.enrolment_permission
        mandatory_telekom_hardware_supply = (
            customer_id.mandatory_telekom_hardware_supply
        )
        if not all(
            flag and flag in valid_mdm_values
            for flag in [
                mdm_enrolment_access,
                mdm_enrolment_permission,
                mandatory_telekom_hardware_supply,
            ]
        ):
            invalid_fields["mdm_data"] = True
        return invalid_fields

    def process_dep_ids_utilising_mdm(self, dep_customer_id, customer_id):
        """Process SOL and MDM data and return allowed DEPs

        Args:
            dep_customer_id (recordset): Record of the DEP customer.
            customer_id (recordset): Record of the customer.

        Returns:
            list or recordset: List of allowed DEP IDs.
        """
        allowed_deps = False
        # If the SO MDM data is invalid, return the false
        product_brand = self.product_brand_id.name
        if not customer_id or not product_brand or product_brand.upper() != "APPLE":
            return allowed_deps

        invalid_data = self.invalid_mdm_configurations(customer_id)
        if invalid_data["disable_utilising_mdm_logic"] or invalid_data["mdm_data"]:
            return allowed_deps

        mdm_enrolment_access = customer_id.enrolment_access
        mdm_enrolment_permission = customer_id.enrolment_permission

        # Below are the default DEP types and shortcuts used in the logic
        custom_dep_type = "customer"
        no_dep_type = "no_dep"
        dep_stock_type = "is_stock"
        t_dep = "T-DEP"  # T DEP name needed to include in the DEP selection

        # NO DEP id needed to include in the DEP selection
        no_dep_id = self.env["dep.customer"].search([("name", "=", "NO DEP")]).id

        if dep_customer_id.dep_type == custom_dep_type:
            if mdm_enrolment_access == "true" and mdm_enrolment_permission == "true":
                allowed_deps = [
                    dep_customer_id.id,
                    no_dep_id,
                ] + self.get_dep_ids_by_type(dep_stock_type)
            else:
                allowed_deps = [dep_customer_id.id]
        elif dep_customer_id.dep_type == no_dep_type:
            allowed_deps = self.get_no_customer_dep_ids()
        elif dep_customer_id.name.upper() == t_dep:
            allowed_deps = self.get_dep_ids_by_type(dep_stock_type) + [no_dep_id]

        return allowed_deps

    def get_product_quantities(
        self,
        companies=None,
        lots=None,
        locations=None,
        skip_availability=None,
        transit=False,
        vendor=False,
        dep_ids=False,
        blocked_id=False,
        device_condition_ids=False,
        warehouses=False,
    ):
        if not transit:
            domain = [("loc_usage", "=", "internal")]
        else:
            domain = [
                "|",
                ("loc_usage", "=", "internal"),
                ("loc_usage", "=", "transit"),
            ]
        if vendor:
            domain = []

        if dep_ids:
            domain.append(("dep_customer_id", "in", dep_ids))

        if device_condition_ids:
            domain.append(("device_condition_id", "in", device_condition_ids))
        domain.append(("product_id", "=", self.id))
        if not skip_availability:
            domain += [
                ("location_id.show_availability", "=", True),
            ]
        if warehouses:
            if transit:
                domain += [
                    "|",
                    ("location_id.warehouse_id", "=", False),
                    ("location_id.warehouse_id", "in", warehouses),
                ]
            else:
                domain += [
                    ("location_id.warehouse_id", "in", warehouses),
                ]
        # locations domain does not apply to products of package type
        if locations and not self.package_type_ids:
            domain += [
                ("location_id", "in", locations),
            ]
        if companies:
            if not transit:
                domain += [("company_id", "in", list(companies))]
            else:
                domain += [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", list(companies)),
                ]
        if lots:
            domain += [("lot_id", "in", lots)]
        if blocked_id:
            domain += [
                "|",
                ("blocked_org_ids", "=", False),
                ("blocked_org_ids", "in", [blocked_id.id]),
            ]
        quants = self.stock_quant_ids.search(domain, order="location_id").filtered(
            lambda quant: quant.available_quantity > 0
        )
        return quants

    def verify_barcode(self, barcode):
        self.ensure_one()
        product_ean = self.barcode_ids.mapped("name")
        product_ean.append(self.barcode) if self.barcode else ""
        error_msg = "Scanned barcode '{}' does not correspond to product '{}'! ".format(
            barcode,
            self.display_name,
        )
        return True if barcode in product_ean else False, error_msg

    def return_barcodes(self):
        return self.mapped("barcode_ids.name") + self.mapped("barcode")


class ProductCategory(models.Model):
    _inherit = "product.category"

    is_vas_category = fields.Boolean(string="Remove from Delivery Slip")
    intrastat_code_id = fields.Many2one(
        "account.intrastat.code",
        string="HS Code",
        readonly=False,
    )
