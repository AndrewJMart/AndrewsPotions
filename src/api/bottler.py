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
    #TESTED AND WORKS V4.00
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

    #TESTED AND WORKS V4.00
    metadata_obj = sqlalchemy.MetaData()
    potion_ledger = sqlalchemy.Table("potion_ledger", metadata_obj, autoload_with=db.engine)
    transactions = sqlalchemy.Table("transactions", metadata_obj, autoload_with=db.engine)

    with db.engine.begin() as connection:
        current_red_ml = 0
        current_green_ml = 0
        current_blue_ml = 0
        current_dark_ml = 0

        # Create Potion Insert Dictionary
        potion_dictionary_list = []
        for potion in potions_delivered:
            potion_name = f"{potion.potion_type[0]}_{potion.potion_type[1]}_{potion.potion_type[2]}_{potion.potion_type[3]}"

            # Update MLs
            current_red_ml -= potion.potion_type[0] * potion.quantity
            current_green_ml -= potion.potion_type[1] * potion.quantity
            current_blue_ml -= potion.potion_type[2] * potion.quantity
            current_dark_ml -= potion.potion_type[3] * potion.quantity

            # Insert Into Potion_Dictionary and append to list
            potion_dictionary_list.append({'item_sku': potion_name, 'quantity': potion.quantity})

        # Insert Potions Into Ledger
        connection.execute(
            sqlalchemy.insert(potion_ledger), potion_dictionary_list
            )

        # Update RGB ML in ledger
        transaction_insert = [
            {
             'gold': 0,
             'red_ml': current_red_ml,
             'green_ml': current_green_ml,
             'blue_ml': current_blue_ml,
             'dark_ml': current_dark_ml
            }
        ]
        connection.execute(
            sqlalchemy.insert(transactions), transaction_insert
            )

        
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    #TESTED AND WORKS V4.00
    # Query Current MLs
    red_ml, green_ml, blue_ml, dark_ml = get_current_ml_totals()

    #Initialize Empty Bottle list
    Bottle_Plan_List = []

    # Begin Connection To Database
    with db.engine.begin() as connection:
        # Grab Existing Quantity Of Potions
        select_stocked_potions = "SELECT SUM(quantity) as total_potions FROM potion_ledger"
        result = connection.execute(sqlalchemy.text(select_stocked_potions))
        all_rows = result.fetchone()
        total_potions = all_rows.total_potions

        # Grab Current Quantity Of Each Potion
        select_stock_per_potion = "SELECT item_sku, SUM(quantity) AS total_potions_per_sku FROM potion_ledger GROUP BY item_sku"
        stocked_potions_result = connection.execute(sqlalchemy.text(select_stock_per_potion))
        all_stocked_potions = stocked_potions_result.fetchall()


        # Store current stock of each potion
        potion_stock_dict = {}
        for potion in all_stocked_potions:
            potion_stock_dict[potion.item_sku] = potion.total_potions_per_sku


        # Grab Max Potions
        max_potion_query = "SELECT * FROM global_inventory"
        result = connection.execute(sqlalchemy.text(max_potion_query))
        row_one = result.fetchone()
        max_potions = row_one.max_potions

        # Grab All Potions
        all_potions = """
        SELECT * FROM potions_table
        """
        result = connection.execute(sqlalchemy.text(all_potions))
        all_potions_list = result.fetchall()

        # For Potions that have not sold yet set quantity to 0
        for potion in all_potions_list:
            if potion.item_sku not in potion_stock_dict:
                potion_stock_dict[potion.item_sku] = 0

    # Loop through all Potions
    for potion in all_potions_list:
        # Check to see if current potion comprises of 15% or more of total possible potions
        if potion_stock_dict[potion.item_sku] < max_potions * .15:
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

            # Find the minimum number of potions to make, capped at 30
            potions_to_make = min(dark_poss, red_poss, green_poss, blue_poss, 
                                  (max_potions * .15) - potion_stock_dict[potion.item_sku])
            
            potions_to_make = max(potions_to_make, 0)

            # Ensure potions don't exceed max_potions
            if potions_to_make + total_potions > max_potions:
                potions_to_make = max_potions - total_potions

            # Update Total Potions And ML Levels
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
                            "quantity": int(potions_to_make),
                        }
                )

    # Return final list
    return Bottle_Plan_List

if __name__ == "__main__":
    print(get_bottle_plan())
