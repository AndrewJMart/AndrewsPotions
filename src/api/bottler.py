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
    
    current_red_ml = first_row.num_red_ml
    current_green_ml = first_row.num_green_ml
    current_blue_ml = first_row.num_blue_ml

    # Loop through delivered potions and update current values
    for potion in potions_delivered:
        potion_name = f"{potion.potion_type[0]}_{potion.potion_type[1]}_{potion.potion_type[2]}_potion"

        # Update MLs
        current_red_ml -= potion.potion_type[0]
        current_green_ml -= potion.potion_type[1]
        current_blue_ml -= potion.potion_type[2]

        # Check if a row with potion_type exists in potions_table
        sql_query = sqlalchemy.text(f"SELECT * FROM potions_table WHERE item_sku = '{potion_name}'")
        with db.engine.begin() as connection:
            result = connection.execute(sql_query)
            existing_row = result.fetchone()

        if existing_row:
            # Update the quantity column
            new_quantity = existing_row.quantity + potion.quantity
            sql_update = sqlalchemy.text(f"UPDATE potions_table SET quantity = {new_quantity} WHERE item_sku = '{potion_name}'")
            with db.engine.begin() as connection:
                connection.execute(sql_update)
        else:
            # Insert a new row into potions_table to represent the new potion
            sql_insert = sqlalchemy.text(f"INSERT INTO potions_table (item_sku, quantity, price, red, green, blue) VALUES (:item_sku, :quantity, :price, :red, :green, :blue)")
            with db.engine.begin() as connection:
                connection.execute(sql_insert, 
                                item_sku=potion_name, 
                                quantity=potion.quantity, 
                                price=30, 
                                red=potion.potion_type[0], 
                                green=potion.potion_type[1], 
                                blue=potion.potion_type[2])

    # Update RGB ML in global_inventory
    sql_to_execute = f"""
        UPDATE global_inventory 
        SET 
            num_green_ml = {current_green_ml},
            num_red_ml = {current_red_ml},
            num_blue_ml = {current_blue_ml}
    """
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
    
    current_red_ml = first_row.num_red_ml
    current_green_ml = first_row.num_green_ml
    current_blue_ml = first_row.num_blue_ml

    #Initialize Empty Bottle list
    Bottle_Plan_List = []
    
    if current_red_ml >= 100:
        # Calculate How Many Potions To Make
        potions_to_make = current_red_ml // 100
        Bottle_Plan_List.append(
                {
                    "potion_type": [100, 0, 0, 0],
                    "quantity": potions_to_make,
                }
        )
    if current_green_ml >= 100:
        potions_to_make = current_green_ml // 100
        Bottle_Plan_List.append(
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": potions_to_make,
                }
        )
    if current_blue_ml >= 100:
        potions_to_make = current_blue_ml // 100
        Bottle_Plan_List.append(
                {
                    "potion_type": [0, 0, 100, 0],
                    "quantity": potions_to_make,
                }
        )
    
    # Return final list
    return Bottle_Plan_List


if __name__ == "__main__":
    print(get_bottle_plan())
