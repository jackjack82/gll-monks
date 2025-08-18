from markupsafe import Markup
from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            self._update_order_note_with_description(line)
        return lines

    def write(self, values):
        result = super().write(values)
        if "product_id" in values:
            for line in self:
                self._update_order_note_with_description(line)
        return result

    def _update_order_note_with_description(self, line):
        if line.product_id and line.product_id.description_pickingout:
            order = line.order_id
            current_note = order.note or ""
            description = line.product_id.description_pickingout

            # Add the description to the note with a line break
            if current_note:
                new_note = Markup("%s<br/>%s") % (current_note, description)
                order.write({"note": new_note})
            else:
                order.write({"note": description})
