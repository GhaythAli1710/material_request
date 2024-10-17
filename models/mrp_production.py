from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    material_request_id = fields.Many2one(
        comodel_name='material.request',
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
            'view_mode': 'form',
            'res_id': self.material_request_id.id,
            'target': 'current',
        }
