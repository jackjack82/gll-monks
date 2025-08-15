from odoo import _, fields, models
from odoo.exceptions import UserError


class GllPricelist(models.Model):
    _name = "gll.pricelist"
    _description = "Gll Price List"

    price = fields.Float("Price")
    min_weight = fields.Float("Min Kg")
    max_weight = fields.Float("Max Kg")
    max_pack_num = fields.Integer("Max colli")
    rounding = fields.Float("Arrotondamento")
    package_type_id = fields.Many2one("stock.package.type", "Pallet")
    state_id = fields.Many2one("res.country.state", string="State")
    volume = fields.Float("Volume")

    def select_gll_pricelist(self, weight, pack_num, volume, package_type_id):
        """Given some input parameters, select the pricelist
        and return the price"""
        domain = [
            ("weight", ">=", self.min_weight),
            ("weight", "<=", self.max_weight),
        ]
        pricelists = self.search(domain)
        if not pricelists:
            raise UserError(_("No pricelists found for the packages in the transfer."))
        if len(pricelists) > 1:
            raise UserError(
                _("Multiple pricelists found for the packages in the transfer.")
            )
        return pricelists

    def compute_delivery_price(
        self,
        weight,
    ):
        pass
