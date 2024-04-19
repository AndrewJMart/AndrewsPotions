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
    #TESTED AND WORKS V3.00
    # Grab initial gold / Mls
    initial_query = """
    SELECT 
        SUM(red_ml) AS total_red_ml,
        SUM(green_ml) AS total_green_ml,
        SUM(blue_ml) AS total_blue_ml,
        SUM(dark_ml) AS total_dark_ml
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
        current_dark_ml = first_row.total_dark_ml
    else:
        current_red_ml = 0
        current_green_ml = 0
        current_blue_ml = 0
        current_dark_ml = 0

    return current_red_ml, current_green_ml, current_blue_ml, current_dark_ml

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    # Tested and Works V3.00
    with db.engine.begin() as connection:
        current_red_ml = 0
        current_green_ml = 0
        current_blue_ml = 0
        current_dark_ml = 0
        # Loop through delivered potions and update current values
        for potion in potions_delivered:
            potion_name = f"{potion.potion_type[0]}_{potion.potion_type[1]}_{potion.potion_type[2]}_{potion.potion_type[3]}"

            # Update MLs
            current_red_ml -= potion.potion_type[0] * potion.quantity
            current_green_ml -= potion.potion_type[1] * potion.quantity
            current_blue_ml -= potion.potion_type[2] * potion.quantity
            current_dark_ml -= potion.potion_type[3] * potion.quantity

            # Insert Into Potion Ledger
            insert_into_ledger = f"""INSERT INTO potion_ledger (item_sku, quantity) 
                            VALUES ('{potion_name}', {potion.quantity})"""
            connection.execute(sqlalchemy.text(insert_into_ledger))

        # Update RGB ML in ledger
        insert_bottle_transaction = f"""INSERT INTO transactions (gold, red_ml, green_ml, blue_ml, dark_ml) 
        VALUES (0, {current_red_ml}, {current_green_ml}, {current_blue_ml}, {current_dark_ml})"""
        result = connection.execute(sqlalchemy.text(insert_bottle_transaction))
        
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # TESTED AND WORKS V3.00

    # Query Current MLs
    red_ml, green_ml, blue_ml, dark_ml = get_current_ml_totals()

    #Initialize Empty Bottle list
    Bottle_Plan_List = []

    # Begin Connection To Database
    with db.engine.begin() as connection:
        # Grab Existing Quantity Of Potions
        select_stocked_potions = f"SELECT SUM(quantity) as total_potions FROM potion_ledger"
        result = connection.execute(sqlalchemy.text(select_stocked_potions))
        all_rows = result.fetchone()
        total_potions = all_rows.total_potions

        # Grab Max Potions
        max_potion_query = f"SELECT * FROM global_inventory"
        result = connection.execute(sqlalchemy.text(max_potion_query))
        row_one = result.fetchone()
        max_potions = row_one.max_potions

        # Grab All Potions
        all_potions = """
        SELECT * FROM potions_table
        """
        result = connection.execute(sqlalchemy.text(all_potions))
        all_potions_list = result.fetchall()

    # Loop through all Potions
    for potion in all_potions_list:
        # Required ML Per Potion
        dark_per_potion = potion.dark
        red_per_potion = potion.red
        green_per_potion = potion.green
        blue_per_potion = potion.blue
        # Calculate Num Of Possible Potions
        if dark_per_potion == 0:
            dark_poss = 10000
        else:
            dark_poss = dark_ml // dark_per_potion

        if red_per_potion == 0:
            red_poss = 10000
        else:
            red_poss = red_ml // red_per_potion

        if green_per_potion == 0:
            green_poss = 10000
        else:
            green_poss = green_ml // green_per_potion

        if blue_per_potion == 0:
            blue_poss = 10000
        else:
            blue_poss = blue_ml // blue_per_potion

        # Find the minimum number of potions to make, capped at 10
        potions_to_make = min(dark_poss, red_poss, green_poss, blue_poss, 10)

        # Ensure potions don't exceed max_potions
        if potions_to_make + total_potions > max_potions:
            potions_to_make = max_potions - total_potions

        # Update Total Potions And ML Levels
        #Total Potions
        total_potions += potions_to_make
        #ML
        red_ml -= red_per_potion * potions_to_make
        green_ml -= green_per_potion * potions_to_make
        blue_ml -= blue_per_potion * potions_to_make
        dark_ml -= dark_per_potion * potions_to_make

        if potions_to_make > 0:
            Bottle_Plan_List.append(
                    {
                        "potion_type": [red_per_potion, green_per_potion, blue_per_potion, dark_per_potion],
                        "quantity": potions_to_make,
                    }
            )

    # Return final list
    return Bottle_Plan_List

if __name__ == "__main__":
    print(get_bottle_plan())
