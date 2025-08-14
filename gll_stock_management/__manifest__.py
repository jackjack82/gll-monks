# © 2025 webmonks
{
    "name": "GLL Stock management",
    "category": "Inventory",
    "summary": "This module handle GLL stock management.",
    "license": "OPL-1",
    "description": "GLL Stock Workflow",
    "version": "18.0.1.1.1",
    "author": "Webmonks SRL",
    "website": "https://github.com/OCA/partner-contact",
    "depends": [
        "stock_delivery",
        "stock",
        "sale",
        "purchase",
    ],
    "external_dependencies": {},
    "assets": {
        "web.assets_backend": [],
    },
    "data": [
        # data files
        "data/data.xml",
        # View files
        "views/stock_picking.xml",
        "views/stock_move_line.xml",
        "views/res_partner.xml",
        "views/stock_package_type.xml",
        "views/gll_pricelist.xml",
        "views/txt_import_wizard_views.xml",
        # security
        "security/ir.model.access.csv",
    ],
    # Technical
    "installable": True,
    "auto_install": False,
    "application": False,
}
