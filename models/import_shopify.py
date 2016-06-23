from openerp import models, fields, api, _
import shopify
import requests

import datetime
import yaml
import pytz
import json


class import_shopify(models.Model):

    _name = 'import.shopify'

    name = fields.Char("Shop Name")
    api_key_shopify = fields.Char("API Key")
    password_shopify = fields.Char("Password")
    last_import_customer = fields.Datetime('last import customer')
    last_import_product = fields.Datetime('last import product')
    last_import_sale_order = fields.Datetime('last import sale order')
    temp_date_customer = fields.Char("Last Updated Customers Date")
    temp_date_product = fields.Char("Last Updated Products Date")
    temp_date_sale_order = fields.Char("Last Updated Sale Order Date")

    @api.one
    def import_customer(self):
        self.last_import_customer = datetime.datetime.now()
        tz = pytz.timezone(self._context.get('tz'))
        berlin_now = datetime.datetime.now(tz)
        if self.temp_date_customer:
            min_date = self.temp_date_customer
            self.temp_date_customer = str(berlin_now.date())+" "+str(berlin_now.time().replace(microsecond=0))
            max_date = self.temp_date_customer
            customer_list = requests.get("https://bista-bipin.myshopify.com/admin/customers.json?updated_at_min=%s&updated_at_max=%s"%(min_date,max_date),
                                   auth=(self.api_key_shopify, self.password_shopify))
        else:
            self.temp_date_customer = str(berlin_now.date())+" "+str(berlin_now.time().replace(microsecond=0))
            customer_list = requests.get("https://bista-bipin.myshopify.com/admin/customers.json?updated_at_max=%s"%(self.temp_date_customer),
                                   auth=(self.api_key_shopify, self.password_shopify))
        str_content = customer_list.__dict__.get('_content')
        customer_list = yaml.load(str_content).get('customers')
        res_partner_obj = self.env['res.partner']
        for customer in customer_list:
            print "-------------",customer
            vals = {}
            vals.update({'name': customer.get('first_name') + " " + customer.get('last_name'),
                         'comment': customer.get('note'),
                         'shopif_id':customer.get('id')})
            customer_add_dict = customer.get('addresses')[0]
            vals.update({'street': customer_add_dict.get('address1'),
                         'street2': customer_add_dict.get('address2'),
                         'city': customer_add_dict.get('city'),
                         'zip': customer_add_dict.get('zip')})
            res_partner_rec = res_partner_obj.search([('shopif_id', '=', customer.get('id'))])
            if res_partner_rec:
                res_partner_rec.write(vals)
            else:
                res_partner_obj.create(vals)

    @api.one
    def import_product(self):
        self.last_import_product = datetime.datetime.now()
        tz = pytz.timezone(self._context.get('tz'))
        berlin_now = datetime.datetime.now(tz)
        if self.temp_date_product:
            min_date = self.temp_date_product
            self.temp_date_product = str(berlin_now.date())+" "+str(berlin_now.time().replace(microsecond=0))
            max_date = self.temp_date_product
            products_list = requests.get("https://bista-bipin.myshopify.com/admin/products.json?updated_at_min=%s&updated_at_max=%s"%(min_date,max_date),
                                   auth=(self.api_key_shopify, self.password_shopify))
        else:
            self.temp_date_product = str(berlin_now.date())+" "+str(berlin_now.time().replace(microsecond=0))
            products_list = requests.get("https://bista-bipin.myshopify.com/admin/products.json?updated_at_max=%s"%(self.temp_date_product),
                                   auth=(self.api_key_shopify, self.password_shopify))
        str_content = products_list.__dict__.get('_content')
        json_acceptable_string = str_content.replace("'", "/")
        product_list = json.loads(json_acceptable_string).get('products')
        product_template_obj = self.env['product.template']
        product_att_line_obj = self.env['product.attribute.line']
        product_att_val_obj = self.env['product.attribute.value']
        product_att_obj = self.env['product.attribute']
        vals = {}
        for product in product_list:
            print "-------",product
            product_option_list = product.get('options')
            vals.update({'name': product.get('title'),
                    'type': 'consu',
                    'shopif_id':product.get('id'),
                    })
            product_template_rec = product_template_obj.search([('shopif_id', '=', product.get('id'))])
            if product_template_rec:
                product_template_rec.write(vals)
            else:
                product_template_new = product_template_obj.create(vals)

            for option in product_option_list:
                product_att_rec = product_att_obj.search([('name', '=', option.get('name')),
                                                          ('shopif_id', '=', option.get('id'))])
                if product_att_rec:
                    list_values = []
                    for value in option.get('values'):
                        product_att_val_rec = product_att_val_obj.search([('name', '=', value),
                                                            ('attribute_id', '=', product_att_rec.id)])
                        if product_att_val_rec:
                            list_values.append(product_att_val_rec.id)
                        else:
                            new_create_arr_id = product_att_val_obj.create({'name': value,
                                                        'attribute_id': product_att_rec.id})
                            list_values.append(new_create_arr_id.id)
                    product_att_line_rec = product_att_line_obj.search([('attribute_id', '=', product_att_rec.id)])
                    if product_att_line_rec:
                        product_att_line_rec.write({'value_ids':[(6,0,list_values)]})
                        product_template_rec.write({'attribute_line_ids': [(4,product_att_line_rec.ids)]})
                    else:
                        product_att_line_rec = product_att_line_obj.create({
                                             'product_tmpl_id':product_template_new.id,
                                             'attribute_id': product_att_rec.id,
                                             'value_ids':[(4,list_values)]})
                        product_template_new.write({'attribute_line_ids': [(4,product_att_line_rec.ids)]})
                else:
                    list_values = []
                    product_att_new = product_att_obj.create({'name': option.get('name'),
                                                              'shopif_id': option.get('id')})
                    for value in option.get('values'):
                        new_create_arr_id = product_att_val_obj.create({'name': value,
                                                        'attribute_id': product_att_new.id})
                        list_values.append(new_create_arr_id.id)
                    if product_template_rec:
                        product_att_line_rec = product_att_line_obj.create({
                                             'product_tmpl_id':product_template_rec.id,
                                             'attribute_id': product_att_new.id,
                                             'value_ids':[(4,list_values)]})
                        product_template_rec.write({'attribute_line_ids': [(4,product_att_line_rec.ids)]})
                    else:
                        product_att_line_rec = product_att_line_obj.create({
                                             'product_tmpl_id':product_template_new.id,
                                             'attribute_id': product_att_new.id,
                                             'value_ids':[(4,list_values)]})
                        product_template_new.write({'attribute_line_ids': [(4,product_att_line_rec.ids)]})
            product_product_obj = self.env['product.product']
            product_variant_list = product.get('variants')
            product_attribute_value_obj = self.env['product.attribute.value']
            for variant in product_variant_list:
                product_attribute_value_rec = product_attribute_value_obj.search(['|','|',('name','=',variant.get('option1')),
                                                                                 ('name','=',variant.get('option2')),
                                                                                  ('name','=',variant.get('option3'))])
                product_template_rec = product_template_obj.search([('shopif_id','=',variant.get('product_id'))])
                product_product_rec = product_product_obj.search([('product_tmpl_id','=',product_template_rec.id),
                                                                  ('attribute_value_ids','in',product_attribute_value_rec.ids)])
                for rec in product_product_rec:
                    if all(x in product_attribute_value_rec.ids for x in rec.attribute_value_ids.ids):
                        rec.write({'shopif_id': variant.get('id')})

    @api.one
    def import_sale_order(self):
        self.last_import_sale_order = datetime.datetime.now()
        self.import_customer()
        self.import_product()
        tz = pytz.timezone(self._context.get('tz'))
        berlin_now = datetime.datetime.now(tz)
        if self.temp_date_sale_order:
            min_date = self.temp_date_sale_order
            self.temp_date_sale_order = str(berlin_now.date())+" "+str(berlin_now.time().replace(microsecond=0))
            max_date = self.temp_date_sale_order
            orders_list = requests.get("https://bista-bipin.myshopify.com/admin/orders.json?updated_at_min=%s&updated_at_max=%s"%(min_date,max_date),
                                   auth=(self.api_key_shopify, self.password_shopify))
        else:
            self.temp_date_sale_order = str(berlin_now.date())+" "+str(berlin_now.time().replace(microsecond=0))
            orders_list = requests.get("https://bista-bipin.myshopify.com/admin/orders.json?updated_at_max=%s"%(self.temp_date_sale_order),
                                   auth=(self.api_key_shopify, self.password_shopify))

        str_content = orders_list.__dict__.get('_content')
        json_acceptable_string = str_content.replace("'", "/")
        order_list = json.loads(json_acceptable_string).get('orders')
        sale_order_obj = self.env['sale.order']
        res_partner_obj = self.env['res.partner']
        for order in order_list:
            print "--------",order
            res_partner_rec = res_partner_obj.search([('shopif_id','=',order.get('customer').get('id'))])
            sale_new = sale_order_obj.create({'partner_id': res_partner_rec.id,
                                              'state': 'manual',
                                              'client_order_ref': order.get('note'),
                                              'amount_tax': order.get('total_tax')})
            for line_item in order.get('line_items'):
                product_product_rec = self.env['product.product'].search([('shopif_id','=',line_item.get('variant_id'))])
                self.env['sale.order.line'].create({'product_id':product_product_rec.id,
                                                'order_id': sale_new.id,
                                                'name':product_product_rec.name,
                                                'price_unit': line_item.get('price'),
                                                'product_uom_qty': line_item.get('quantity')})
