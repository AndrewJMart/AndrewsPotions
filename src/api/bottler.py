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

def get_current_ml_totals():
    # Grab initial gold / Mls
    initial_query = """
    SELECT 
        SUM(red_ml) AS total_red_ml,
        SUM(green_ml) AS total_green_ml,
        SUM(blue_ml) AS total_blue_ml
    FROM transactions
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()

    # Extracting the sums of each potion type
    if first_row:
        current_red_ml = first_row.total_red_ml
        current_green_ml = first_row.total_green_ml
        current_blue_ml = first_row.total_blue_ml
    else:
        current_red_ml = 0
        current_green_ml = 0
        current_blue_ml = 0

    return current_red_ml, current_green_ml, current_blue_ml

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    # Tested and Works V2.2
    with db.engine.begin() as connection:
        current_red_ml = 0
        current_green_ml = 0
        current_blue_ml = 0
        # Loop through delivered potions and update current values
        for potion in potions_delivered:
            potion_name = f"{potion.potion_type[0]}_{potion.potion_type[1]}_{potion.potion_type[2]}_potion"

            # Update MLs
            current_red_ml -= potion.potion_type[0] * potion.quantity
            current_green_ml -= potion.potion_type[1] * potion.quantity
            current_blue_ml -= potion.potion_type[2] * potion.quantity

            # Check if a row with potion_type exists in potions_table
            select_sku = f"SELECT * FROM potions_table WHERE item_sku = '{potion_name}'"
            result = connection.execute(sqlalchemy.text(select_sku))
            existing_row = result.fetchone()

            if not existing_row:
                # Insert a new row into potions_table to represent the new potion
                insert_into_table = f"""INSERT INTO potions_table (item_sku, price, red, green, blue) 
                                VALUES ('{potion_name}', 35, {potion.potion_type[0]}, 
                                {potion.potion_type[1]}, {potion.potion_type[2]})"""
                connection.execute(sqlalchemy.text(insert_into_table))

            # Insert a new row into potions_table to represent the new potion
            insert_into_ledger = f"""INSERT INTO potion_ledger (item_sku, quantity) 
                            VALUES ('{potion_name}', {potion.quantity})"""
            connection.execute(sqlalchemy.text(insert_into_ledger))

        # Update RGB ML in ledger
        insert_bottle_transaction = f"""INSERT INTO transactions (gold, red_ml, green_ml, blue_ml) 
        VALUES (0, {current_red_ml}, {current_green_ml}, {current_blue_ml})"""
        result = connection.execute(sqlalchemy.text(insert_bottle_transaction))
        
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # TESTED AND WORKS V2.2

    # Query Current MLs
    red_ml, green_ml, blue_ml = get_current_ml_totals()

    #Initialize Empty Bottle list
    Bottle_Plan_List = []
    total_potions = 0

    # Grab Total Number of existing potions
    select_stocked_potions = f"SELECT SUM(quantity) as total_potions FROM potion_ledger"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_stocked_potions))
        all_rows = result.fetchone()
        total_potions = all_rows.total_potions
    
    if red_ml >= 100 and total_potions < 50:
        # Calculate How Many Potions To Make
        potions_to_make = red_ml // 100

        if potions_to_make + total_potions > 50:
            potions_to_make = 50 - total_potions

        Bottle_Plan_List.append(
                {
                    "potion_type": [100, 0, 0, 0],
                    "quantity": potions_to_make,
                }
        )

        total_potions += potions_to_make
        
    if green_ml >= 100 and total_potions < 50:
        potions_to_make = green_ml // 100

        if potions_to_make + total_potions > 50:
            potions_to_make = 50 - total_potions
            
        Bottle_Plan_List.append(
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": potions_to_make,
                }
        )

        total_potions += potions_to_make

    if blue_ml >= 100 and total_potions < 50:
        potions_to_make = blue_ml // 100

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
