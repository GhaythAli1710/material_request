from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

REQUEST_STATES = [
    ('draft', "Draft"),
    ('pending', "Pending"),
    ('approved', "Approved"),
    ('ordered', "Ordered"),
    ('done', "Done"),
    ('refused', "Refused"),
]

REQUEST_ACTIONS = [
    ('none', "None"),
    ('design', "Design"),
    ('purchase', "Purchase"),
    ('manufacture', "Manufacture"),
]


class MaterialRequest(models.Model):
    _name = 'material.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Material Request'

    name = fields.Char(
        string='Name',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: self.env.uid,
        ondelete='restrict',
    )
    date_request = fields.Datetime(
        string='Request Date',
        required=True,
        readonly=True,
        copy=False,
        default=fields.Datetime.now,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        ondelete='restrict',
    )
    product_qty = fields.Float(
        string='Quantity',
        required=True,
    )
    note = fields.Text(
        string='Note',
    )
    action = fields.Selection(
        selection=REQUEST_ACTIONS,
        string='Action',
        copy=False,
        default='none',
    )
    state = fields.Selection(
        selection=REQUEST_STATES,
        string='Status',
        readonly=True,
        copy=False,
        default='draft',
    )
    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        copy=False,
        ondelete='restrict',
    )
    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )
    manufacturing_order_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )
    design_eco_id = fields.Many2one(
        comodel_name='mrp.eco',
        string='Product ECO',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'material.request') or _('New')
        res = super(MaterialRequest, self).create(vals)
        return res

    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'pending'
                group_xmlid = self.env.ref('material_request.group_material_request_approver',
                                           raise_if_not_found=False)
                if group_xmlid:
                    group = self.env['res.groups'].search([('id', '=', group_xmlid.id)])
                    recipient_partners = []
                    for recipient in group.users:
                        recipient_partners.append(
                            recipient.partner_id.id
                        )
                    if recipient_partners:
                        record.message_post(
                            body="A Material Request has been added to you approve it.",
                            message_type="notification",
                            partner_ids=recipient_partners,
                        )

    def action_approve(self):
        for record in self:
            if record.state == 'pending':
                record.state = 'approved'
                group_xmlid = self.env.ref('material_request.group_material_request_implementer',
                                           raise_if_not_found=False)
                if group_xmlid:
                    group = self.env['res.groups'].search([('id', '=', group_xmlid.id)])
                    recipient_partners = []
                    for recipient in group.users:
                        recipient_partners.append(
                            recipient.partner_id.id
                        )
                    if recipient_partners:
                        record.message_post(
                            body="A Material Request has been added to you order it.",
                            message_type="notification",
                            partner_ids=recipient_partners,
                        )

    def action_order(self):
        accepted_purchase_records = []
        for record in self:
            if record.state != 'approved':
                continue
            if not record.action or record.action == 'none':
                raise ValidationError(_(
                    "The request [ %s ] doesn't have action, Please select a suitable action.",
                    record.name
                ))
            if record.action == 'purchase' and not record.vendor_id:
                raise ValidationError(_(
                    "The request [ %s ] doesn't have Vendor for order, Please enter a Vendor.",
                    record.name
                ))
            if record.action == 'manufacture' and record.product_qty == 0.00:
                raise ValidationError(_(
                    "The request [ %s ] doesn't have Quantity for order, Please Reset a Request and pass positive "
                    "quantity.",
                    record.name
                ))
            record.state = 'ordered'
            if record.action == 'purchase':
                self._process_purchase_action(record, accepted_purchase_records)
            elif record.action == 'manufacture':
                self._process_manufacture_action(record)
            elif record.action == 'design':
                self._process_design_action(record)
            self._notify_group(record)

    def _process_purchase_action(self, record, accepted_purchase_records):
        for item in accepted_purchase_records:
            if record.vendor_id.id == item['vendor_id']:
                record.purchase_order_id = self.env['material.request'].browse(
                    item['record_id']).purchase_order_id.id
                break
        if not record.purchase_order_id:
            accepted_purchase_records.append({"record_id": record.id, "vendor_id": record.vendor_id.id})
            record.purchase_order_id = self.env['purchase.order'].create({'partner_id': record.vendor_id.id})
        record.purchase_order_id.material_request_ids.ids.append(record.id)
        order_line_id = self.env['purchase.order.line'].create({
            'order_id': record.purchase_order_id.id,
            'product_id': record.product_id.id,
            'product_qty': record.product_qty,
        })
        record.purchase_order_id.order_line.ids.append(order_line_id.id)

    def _process_manufacture_action(self, record):
        record.manufacturing_order_id = self.env['mrp.production'].create({
            'product_id': record.product_id.id,
            'product_qty': record.product_qty,
            'material_request_id': record.id,
        })

    def _process_design_action(self, record):
        record.design_eco_id = self.env['mrp.eco'].create({
            'name': record.name,
            'type_id': self.env.ref('material_request.eco_type_design').id,
            'type': 'product',
            'product_tmpl_id': record.product_id.product_tmpl_id.id,
            'stage_id': self.env.ref('material_request.eco_stage_new').id,
            'material_request_id': record.id,
        })

    def _notify_group(self, record):
        action_groups = {
            'purchase': 'material_request.group_material_request_purchase_person',
            'manufacture': 'material_request.group_material_request_manufacturing_person',
            'design': 'material_request.group_material_request_design_person',
        }
        group_xmlid = self.env.ref(action_groups.get(record.action), raise_if_not_found=False)
        if group_xmlid:
            group = self.env['res.groups'].search([('id', '=', group_xmlid.id)])
            recipient_partners = [user.partner_id.id for user in group.users]
            if recipient_partners:
                record.message_post(
                    body="A Material Request has been added to you.",
                    message_type="notification",
                    partner_ids=recipient_partners,
                )

    def action_done(self):
        for record in self:
            if record.state == 'ordered':
                record.state = 'done'

    def action_view_related_order(self):
        self.ensure_one()
        if self.action == 'purchase':
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': self.purchase_order_id.id,
                'target': 'current',
            }
        elif self.action == 'manufacture':
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'view_mode': 'form',
                'res_id': self.manufacturing_order_id.id,
                'target': 'current',
            }

    def action_view_related_eco(self):
        self.ensure_one()
        if self.action == 'design':
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.eco',
                'view_mode': 'form',
                'res_id': self.design_eco_id.id,
                'target': 'current',
            }

    def action_refuse(self):
        self.ensure_one()
        self.state = 'refused'

    def action_reset(self):
        self.ensure_one()
        self.state = 'draft'

    def unlink(self):
        for record in self:
            if record.state == 'draft':
                super(MaterialRequest, record).unlink()
