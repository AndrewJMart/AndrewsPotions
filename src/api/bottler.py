from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    sql_to_execute = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        first_row = result.fetchone()
    
    current_green_ml = first_row[2]
    current_green_potions = first_row[1]

    # Loop through delivered potions and update current values
    for potion in potions_delivered:
        if potion.potion_type[1] == 100:
            current_green_ml -= 100 * potion.quantity
            current_green_potions += potion.quantity

    # Update Green ML
    sql_to_execute = f"UPDATE global_inventory SET num_green_ml = {current_green_ml}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
    
    # Update Number Of Green Potions
    sql_to_execute = f"UPDATE global_inventory SET num_green_potions = {current_green_potions}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial Query Of Global_Inventory 
    sql_to_execute = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        first_row = result.fetchone()
    
    current_green_ml = first_row[2]

    if current_green_ml >= 100:
        # Calculate How Many Potions To Make
        potions_to_make = current_green_ml // 100

        return [
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": potions_to_make,
                }
            ]
    else:
        return []


if __name__ == "__main__":
    print(get_bottle_plan())
