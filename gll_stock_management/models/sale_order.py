from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_type = fields.Selection([
        ('deliveries', 'Deliveries'),
        ('receipts', 'Receipts'),
    ])