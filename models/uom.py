# © 2025 webmonks

from odoo import fields, models


class UoM(models.Model):
    _inherit = "uom.uom"

    import_code = fields.Char(
        string="Import Code", help="Code used for importing UoM from external files"
    )
