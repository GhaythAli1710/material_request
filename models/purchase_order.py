from odoo import models, fields, api, _


class MaterialRequest(models.Model):
    _inherit = 'purchase.order'

    material_request_ids = fields.One2many(
        comodel_name='material.request',
        inverse_name='purchase_order_id',
        string='Material Request',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )

    def action_view_material_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_mode': 'tree',
            'domain': [('id', 'in', self.material_request_ids.ids)],
            'target': 'current',
        }
