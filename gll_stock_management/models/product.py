# © 2025 webmonks

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    package_type = fields.Selection(
        [
            ("single", "Singolo"),
            ("box", "Scatola"),
        ],
        string="Tipo Pacchetto",
    )
    # pick_service_type = fields.Selection(
    #     related="product_tmpl_id.service_type",
    # )

    # Modify volume field to have 5 decimal precision
    volume = fields.Float("Volume", digits=(16, 5), help="The volume in cubic meters.")

    colli_per_strato = fields.Integer(string="Colli per strato")
    strati_per_pallet = fields.Integer(string="Strati per pallet")

    @api.onchange("volume")
    def _onchange_volume(self):
        """Round volume to 5 decimal places"""
        if self.volume:
            self.volume = round(self.volume, 5)

    def _get_description(self, picking_type_id):
        """override completely the original to avoid using the use of
        description fields
        """
        self.ensure_one()
        return self.name


class ProductTemplate(models.Model):
    _inherit = "product.template"

    package_type = fields.Selection(
        related="product_variant_ids.package_type",
        string="Tipo Pacchetto",
        readonly=False,
    )

    pick_service_type = fields.Selection(
                [
                        ("warehouse", "Warehouse"),
                        ("transport", "Transport"),
                        ("accessories", "Accessories"),
                        ("additional", "Additional"),
                        ("fixed", "Fixed"),
                        ("variable", "Variable"),
            ],
                string = "Service Type",
                copy=False,
        )


    # Modify volume field to have 5 decimal precision
    volume = fields.Float("Volume", digits=(16, 5), help="The volume in cubic meters.")

    colli_per_strato = fields.Integer(
        related="product_variant_ids.colli_per_strato",
        string="Colli per strato",
        readonly=False,
    )
    strati_per_pallet = fields.Integer(
        related="product_variant_ids.strati_per_pallet",
        string="Strati per pallet",
        readonly=False,
    )

    @api.onchange("volume")
    def _onchange_volume(self):
        """Round volume to 5 decimal places"""
        if self.volume:
            self.volume = round(self.volume, 5)
