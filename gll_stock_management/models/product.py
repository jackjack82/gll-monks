# © 2025 webmonks

from odoo import _, api, fields, models
from odoo.exceptions import UserError

SERVICE_TYPE = [
    ("warehouse", "Warehouse"),
    ("transport", "Transport"),
    ("accessories", "Accessories"),
    ("additional", "Additional"),
    ("fixed", "Fixed"),
    ("variable", "Variable"),
    ("subscription", "Subscription"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    package_type = fields.Selection(
        related="product_variant_ids.package_type",
        string="Tipo Pacchetto",
        readonly=False,
    )

    warehouse_type = fields.Selection(
        related="product_variant_ids.warehouse_type",
        string="Warehouse Type",
        readonly=False,
    )
    default_service = fields.Boolean(
        related="product_variant_ids.default_service",
        readonly=False,
    )

    inconvenient_city_service = fields.Boolean(
        related="product_variant_ids.inconvenient_city_service",
        string="Inconvenient City Service",
        readonly=False,
        help="If checked, this product will be added as a service line when a picking is sent to an inconvenient city",
    )

    # Fields for transport tariff calculation
    tariff_percentage = fields.Float(
        related="product_variant_ids.tariff_percentage",
        string="Tariff Percentage",
        readonly=False,
        help="Percentage of transport tariff to apply",
    )
    tariff_min = fields.Float(
        related="product_variant_ids.tariff_min",
        string="Min Price",
        readonly=False,
        help="Minimum price for the service",
    )
    tariff_max = fields.Float(
        related="product_variant_ids.tariff_max",
        string="Max Price",
        readonly=False,
        help="Maximum price for the service",
    )

    pick_service_type = fields.Selection(
        SERVICE_TYPE,
        string="Service Type",
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

    @api.onchange("pick_service_type")
    def onchange_service_type(self):
        if self.pick_service_type and self.type != "service":
            raise UserError(_("Only services can have this type of configuration."))

        # Clear warehouse_type if pick_service_type is not warehouse
        if self.pick_service_type != "warehouse":
            self.warehouse_type = False

    @api.constrains("tariff_percentage", "lst_price", "list_price")
    def _check_price_configuration(self):
        for product in self:
            if product.list_price and product.tariff_percentage:
                raise UserError(
                    _("A product price can either be fixed or in percentage")
                )


class ProductProduct(models.Model):
    _inherit = "product.product"

    package_type = fields.Selection(
        [
            ("single", "Singolo"),
            ("box", "Scatola"),
        ],
        string="Tipo Pacchetto",
    )

    warehouse_type = fields.Selection(
        [
            ("fix", "Diritto Fisso"),
            ("preparation", "Preparazione"),
            ("logistic", "Servizi logistici"),
        ],
        string="Warehouse Type",
    )
    default_service = fields.Boolean(default=False)
    inconvenient_city_service = fields.Boolean(
        string="Inconvenient City Service",
        default=False,
        help="If checked, this product will be added as a service line when a picking is sent to an inconvenient city",
    )

    # Fields for transport tariff calculation
    tariff_percentage = fields.Float(
        "Tariff Percentage", default=0.0, help="Percentage of transport tariff to apply"
    )
    tariff_min = fields.Float("Min Price", help="Minimum price for the service")
    tariff_max = fields.Float("Max Price", help="Maximum price for the service")

    volume = fields.Float("Volume", digits=(16, 5), help="The volume in cubic meters.")

    colli_per_strato = fields.Integer(string="Colli per strato")
    strati_per_pallet = fields.Integer(string="Strati per pallet")

    @api.onchange("pick_service_type")
    def onchange_service_type(self):
        if self.pick_service_type and self.type != "service":
            raise UserError(_("Only services can have this type of configuration."))

        # Clear warehouse_type if pick_service_type is not warehouse
        if self.pick_service_type != "warehouse":
            self.warehouse_type = False

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

    def _get_product_price(self, transport_tariff):
        """Depending on its configuration, the price can be the list
        price or the percentage of the transport tariff amount"""
        self.ensure_one()
        if self.list_price:
            return self.list_price
        # Calculate price based on transport_tariff and percentage
        calculated_price = transport_tariff * self.tariff_percentage / 100
        return max(min(calculated_price, self.tariff_max), calculated_price)

    @api.constrains("tariff_percentage", "lst_price", "list_price")
    def _check_price_configuration(self):
        for product in self:
            if product.list_price and product.tariff_percentage:
                raise UserError(
                    _("A product price can either be fixed or in percentage")
                )
