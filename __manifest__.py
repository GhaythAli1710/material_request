{
    'name': 'Material Request',

    'version': '17.0.2.0.0',

    'summary': """The module Material Request by purchasing, manufacturing or designing it.""",

    'description': """"
     - Add the "Material Request" service to the Inventory.
     - Create a purchase order, a manufacturing order or an ECO from the Material Request. 
     - New Stages on the PLM for Product Design type to handle the Design action from the Material Request.
     """,

    'category': 'Inventory/Purchase/Manufacturing/PLM',

    'author': 'Ghayth Ali',

    'website': 'https://www.linkedin.com/in/ghayth-ali-al1710/',

    'depends': [
        'base',
        'stock',
        'purchase',
        'mail',
        'mrp',
        'plm',
    ],

    'data': [
        'data/material_request_data.xml',
        'data/mrp_eco_data.xml',

        'security/material_request_security.xml',
        'security/ir.model.access.csv',

        'views/material_request_views.xml',
        'views/stock_menus.xml',
        'views/purchase_order_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_eco_views.xml',
    ],

    'installable': True,

    'application': False,
}
