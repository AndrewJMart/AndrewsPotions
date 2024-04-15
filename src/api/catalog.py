from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    #TESTED AND WORKS V2.2

    # Grab all available potions for catalog
    select_stocked_potions = f"""SELECT item_sku, SUM(quantity) AS total_potions FROM potion_ledger 
                                 WHERE quantity > 0 GROUP BY item_sku"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_stocked_potions))
        all_rows = result.fetchall()
    
    # Initialize Empty Catalog Listing
    catalog_listing = []

    # Iterate through each row and append this potion to catalog listing
    for row in all_rows:
        select_potion = f"""SELECT * FROM potions_table 
                                 WHERE item_sku = '{row.item_sku}' """
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text(select_potion))
            potion_metadata = result.fetchone()

        # If potion is not already listed
        catalog_listing.append({
                    "sku": potion_metadata.item_sku,
                    "name": potion_metadata.item_sku,
                    "quantity": row.total_potions,
                    "price": potion_metadata.price,
                    "potion_type": [potion_metadata.red, potion_metadata.green, potion_metadata.blue, 0],
                })
    
    return catalog_listing