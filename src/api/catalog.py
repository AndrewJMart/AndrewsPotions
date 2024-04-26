from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    #TESTED AND WORKS V4.00

    # Grab all available potions for catalog
    select_stocked_potions = f"""SELECT item_sku, SUM(quantity) AS total_potions FROM potion_ledger GROUP BY item_sku"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_stocked_potions))
        all_rows = result.fetchall()
    
    # Initialize Empty Catalog Listing
    catalog_listing = []

    # Iterate through each row and append this potion to catalog listing
    for row in all_rows:
        if row.total_potions > 0:
            select_potion = f"""SELECT * FROM potions_table 
                                    WHERE item_sku = '{row.item_sku}' """
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text(select_potion))
                potion_metadata = result.fetchone()

            if len(catalog_listing) < 6:
                catalog_listing.append({
                            "sku": potion_metadata.item_sku,
                            "name": potion_metadata.item_sku,
                            "quantity": row.total_potions,
                            "price": potion_metadata.price,
                            "potion_type": [potion_metadata.red, potion_metadata.green, potion_metadata.blue, potion_metadata.dark],
                        })
    
    return catalog_listing