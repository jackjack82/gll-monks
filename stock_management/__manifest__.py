# © 2025 webmonks
{
    "name": "GLL Stock management",
    "category": "Inventory",
    "summary": "This module handle GLL stock management.",
    "license": "OPL-1",
    "description": "Stock Workflow",
    "version": "18.0.1.1.1",
    "author": "Webmonks SRL",
    "website": "http://www.webmonks.de",
    "depends": [
        "base",
        "barcodes",
        "stock_barcode",
        "stock_delivery",
        "stock",
    ],
    "external_dependencies": {},
    "assets": {
        "web.assets_backend": [],
    },
    "data": [
        # View files
        "views/stock_package.xml",
        "views/stock.xml",
    ],
    # Technical
    "installable": True,
    "auto_install": False,
    "application": False,
}
