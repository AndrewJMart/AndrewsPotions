from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # Grab all available potions for catalog
    sql_to_execute = f"SELECT * FROM potions_table WHERE quantity > 0"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        all_rows = result.fetchall()
    
    # Initialize Empty Catalog Listing
    catalog_listing = []

    # Iterate through each row and append this potion to catalog listing
    for row in all_rows:
        catalog_listing.append({
                    "sku": row.item_sku,
                    "name": row.item_sku,
                    "quantity": row.quantity,
                    "price": row.price,
                    "potion_type": [row.red, row.green, row.blue, 0],
                })