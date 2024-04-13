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

    # Tested and Works V2.05

    inital_query = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(inital_query))
        first_row = result.fetchone()
    
    current_red_ml = first_row.num_red_ml
    current_green_ml = first_row.num_green_ml
    current_blue_ml = first_row.num_blue_ml

    # Loop through delivered potions and update current values
    for potion in potions_delivered:
        potion_name = f"{potion.potion_type[0]}_{potion.potion_type[1]}_{potion.potion_type[2]}_potion"

        # Update MLs
        current_red_ml -= potion.potion_type[0] * potion.quantity
        current_green_ml -= potion.potion_type[1] * potion.quantity
        current_blue_ml -= potion.potion_type[2] * potion.quantity

        # Check if a row with potion_type exists in potions_table
        select_sku = f"SELECT * FROM potions_table WHERE item_sku = '{potion_name}'"
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text(select_sku))
            existing_row = result.fetchone()

        if existing_row:
            # Update the quantity column
            new_quantity = existing_row.quantity + potion.quantity
            update_quantity = f"""UPDATE potions_table SET quantity = {new_quantity} 
                                         WHERE item_sku = '{potion_name}'"""
            with db.engine.begin() as connection:
                connection.execute(sqlalchemy.text(update_quantity))
        else:
            # Insert a new row into potions_table to represent the new potion
            insert_new_potion = f"""INSERT INTO potions_table (item_sku, quantity, price, red, green, blue) 
                            VALUES ('{potion_name}', {potion.quantity}, 35, 
                            {potion.potion_type[0]}, {potion.potion_type[1]}, {potion.potion_type[2]})"""
            with db.engine.begin() as connection:
                connection.execute(sqlalchemy.text(insert_new_potion))

    # Update RGB ML in global_inventory
    update_ml = f"""
        UPDATE global_inventory 
        SET 
            num_green_ml = {current_green_ml},
            num_red_ml = {current_red_ml},
            num_blue_ml = {current_blue_ml}
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(update_ml))


    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # TESTED AND WORKS V2.05

    # Initial Query Of Global_Inventory 
    initial_query = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()
    
    current_red_ml = first_row.num_red_ml
    current_green_ml = first_row.num_green_ml
    current_blue_ml = first_row.num_blue_ml

    #Initialize Empty Bottle list
    Bottle_Plan_List = []

    total_potions = 0
    
    if current_red_ml >= 100:
        # Calculate How Many Potions To Make
        potions_to_make = current_red_ml // 100

        if potions_to_make + total_potions > 50:
            potions_to_make = 50 - total_potions

        Bottle_Plan_List.append(
                {
                    "potion_type": [100, 0, 0, 0],
                    "quantity": potions_to_make,
                }
        )

        total_potions += potions_to_make
        
    if current_green_ml >= 100:
        potions_to_make = current_green_ml // 100

        if potions_to_make + total_potions > 50:
            potions_to_make = 50 - total_potions
            
        Bottle_Plan_List.append(
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": potions_to_make,
                }
        )

        total_potions += potions_to_make

    if current_blue_ml >= 100:
        potions_to_make = current_blue_ml // 100

        if potions_to_make + total_potions > 50:
            potions_to_make = 50 - total_potions
        
        Bottle_Plan_List.append(
                {
                    "potion_type": [0, 0, 100, 0],
                    "quantity": potions_to_make,
                }
        )

        total_potions += potions_to_make
    
    # Return final list
    return Bottle_Plan_List


if __name__ == "__main__":
    print(get_bottle_plan())
