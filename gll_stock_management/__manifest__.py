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
    ],
    "external_dependencies": {},
    "assets": {
        "web.assets_backend": [],
    },
    "data": [
        # View files
        "views/stock_picking.xml",
        "views/stock_move_line.xml",
        "views/res_partner.xml",
        "views/stock_package_type.xml",
    ],
    # Technical
    "installable": True,
    "auto_install": False,
    "application": False,
}
