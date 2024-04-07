from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    sql_to_execute = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        first_row = result.fetchone()
        
    number_of_green_potions = first_row[1]

    if number_of_green_potions > 0:
        return [
                {
                    "sku": "green_potion",
                    "name": "green potion",
                    "quantity": number_of_green_potions,
                    "price": 50,
                    "potion_type": [0, 100, 0, 0]
                }
            ]
    return []