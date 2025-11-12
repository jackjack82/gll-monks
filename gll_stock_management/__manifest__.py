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
        "accountant",
        "stock",
        "stock_delivery",
        "sale",
        "purchase",
        "base_address_extended",
    ],
    "external_dependencies": {
        "python": ["xlrd"],
    },
    "assets": {
        "web.assets_backend": [],
    },
    "data": [
        # data files
        "data/data.xml",
        # View files
        "views/account_move.xml",
        "views/stock_picking.xml",
        "views/stock_move_line.xml",
        "views/res_partner.xml",
        "views/stock_package_type.xml",
        "views/gll_pricelist.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
        "views/gll_trip_views.xml",
        "views/sale_order.xml",
        "views/uom_views.xml",
        # security
        "security/ir.model.access.csv",
        # reports
        "reports/picking_reports.xml",
        "reports/logistics_services_invoicing_report.xml",
        "reports/italy_transportation_services_report.xml",
        "reports/report_account_move_entrata_merci.xml",
        "reports/transportation_from_invoice_report.xml",
        # wizard
        "wizard/txt_import_wizard_views.xml",
        "wizard/inconvenient_city_import_wizard.xml",
    ],
    # Technical
    "installable": True,
    "auto_install": False,
    "application": False,
}
