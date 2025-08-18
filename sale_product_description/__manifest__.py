{
    "name": "Sale Product Description",
    "version": "1.0",
    "category": "Sales",
    "summary": "Add product description_pickingout to order notes",
    "description": """
        When an order line is added to a sale order, this module automatically adds
        the product's description_pickingout to the order notes.
    """,
    "depends": ["sale", "stock"],
    "data": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
