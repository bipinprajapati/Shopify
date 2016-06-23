from openerp import models, fields, api

class res_partner(models.Model):

    _inherit = 'res.partner'

    shopif_id = fields.Char('Shopify Customer Id')


class product_template(models.Model):

    _inherit = 'product.template'

    shopif_id = fields.Char('Shopify product Id')


class product_attribute(models.Model):

    _inherit = 'product.attribute'

    shopif_id = fields.Char('Shopify product Id')


class product_product(models.Model):

    _inherit = 'product.product'

    shopif_id = fields.Char('Shopify product Id')


