from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    #TESTED AND WORKS V2.1

    gold = 0
    num_of_red_ml = 0
    num_of_green_ml = 0
    num_of_blue_ml = 0 

    # Looping through receieved barrels and adjusting values to eventually update SupaBase data
    for barrel in barrels_delivered:
        # Update Gold Amount
        gold -= barrel.price * barrel.quantity
        # Red Barrel
        if barrel.potion_type[0] == 1:
            num_of_red_ml += barrel.ml_per_barrel * barrel.quantity
        # Green Barrel
        elif barrel.potion_type[1] == 1:
            num_of_green_ml += barrel.ml_per_barrel * barrel.quantity
        # Blue Barrel
        elif barrel.potion_type[2] == 1:
            num_of_blue_ml += barrel.ml_per_barrel * barrel.quantity

    # Now update the global_inventory to reflect new values
    insert_barrel_transaction = f"""INSERT INTO transactions (gold, red_ml, green_ml, blue_ml) 
    VALUES ({gold}, {num_of_red_ml}, {num_of_green_ml}, {num_of_blue_ml})"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(insert_barrel_transaction))

    return "OK"

def ml_per_gold(barrel):
    return barrel.ml_per_barrel / barrel.price

def find_max_purchasable_amount(barrel, current_gold, total_ml):
    max_purchasable_amount = 1  # At least one barrel can be purchased
    for i in range(2, barrel.quantity + 1):
        quantity_price = barrel.price * i
        quantity_ml = barrel.ml_per_barrel * i
        if current_gold >= quantity_price and total_ml + quantity_ml <= 10000:
            max_purchasable_amount = i
        else:
            break  # Exit the loop if constraints are violated
    return max_purchasable_amount

def get_current_gold():
    with db.engine.begin() as connection:
        # Grab initial gold / Mls
        initial_query = """
        SELECT 
            SUM(gold) AS total_gold
        FROM transactions
        """
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()

        # Extracting the sums of each potion type
        if first_row:
            current_gold = first_row.total_gold
        else:
            current_gold = 0
    return current_gold

def get_current_ml_totals():
    with db.engine.begin() as connection:
        # Grab initial gold / Mls
        initial_query = """
        SELECT 
            SUM(red_ml) AS total_red_ml,
            SUM(green_ml) AS total_green_ml,
            SUM(blue_ml) AS total_blue_ml
        FROM transactions
        """
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

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    # TESTED AND WORKS FOR V2.1

    # Grab current gold and gold benchmark
    with db.engine.begin() as connection:
        initial_query = "SELECT * FROM global_inventory"
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()

        gold_benchmark = first_row.gold_benchmark
        red_benchmark = first_row.red_potion_benchmark

        red_ml, blue_ml, green_ml = get_current_ml_totals()
        total_ml = red_ml + blue_ml + green_ml

        # Query Current Gold
        current_gold = get_current_gold()

        select_red = """
        SELECT * 
        FROM potions_table 
        WHERE red = 100
        """
        result = connection.execute(sqlalchemy.text(select_red))
        red_potion_row = result.fetchone()

        if red_potion_row:
            red_potion_quantity = red_potion_row.quantity
        else:
            red_potion_quantity = 0
    
    # Initialize empty barrel list
    barrel_purchase_list = []

    # Sort catalog on ML_Per_Barrel
    sorted_wholesale_catalog = sorted(wholesale_catalog, key=ml_per_gold, reverse= True)
    print(sorted_wholesale_catalog)

    # Benchmark Eval - If Shop is below gold_benchmark (400) or less than green_potion_benchmark only purchase green barrels
    if current_gold < gold_benchmark:
        #Implement simple selling only green potions
        for barrel in sorted_wholesale_catalog:    
            # Check if barrel is green
            if barrel.potion_type[1] == 1 and current_gold >= barrel.price and "MINI" not in barrel.sku and total_ml + barrel.ml_per_barrel <= 10000:
                # Acquire max amount of said barrel
                max_purchase = find_max_purchasable_amount(barrel, current_gold, total_ml)
                current_gold -= barrel.price * max_purchase
                total_ml += barrel.ml_per_barrel * max_purchase
                
                # Add max quantity amount of barrel to purchase list IN appropriate spot
                barrel_purchase_list.append({
                    "sku": barrel.sku,
                    "quantity": max_purchase,
                })
    else:
        # If above gold threshold then begin buying red barrels (if number of red potions is less than ten)
        if red_potion_quantity <= red_benchmark:
            for barrel in sorted_wholesale_catalog:
                # Check if barrel is red
                if barrel.potion_type[0] == 1 and current_gold >= barrel.price and "MINI" not in barrel.sku and total_ml + barrel.ml_per_barrel <= 10000:
                    # Acquire max amount of said barrel & Update Gold
                    max_purchase = find_max_purchasable_amount(barrel, current_gold, total_ml)
                    current_gold -= barrel.price * max_purchase
                    total_ml += barrel.ml_per_barrel * max_purchase

                    # Add max quantity amount of barrel to purchase list
                    barrel_purchase_list.append({
                        "sku": barrel.sku,
                        "quantity": max_purchase,
                    })
        else:
            # Purchase Max Amount of blue barrels
            for barrel in sorted_wholesale_catalog:
                # Check if barrel is blue
                if barrel.potion_type[2] == 1 and current_gold >= barrel.price and "MINI" not in barrel.sku and total_ml + barrel.ml_per_barrel <= 10000:
                    # Acquire max amount of said barrel & Update Gold
                    max_purchase = find_max_purchasable_amount(barrel, current_gold, total_ml)
                    current_gold -= barrel.price * max_purchase
                    total_ml += barrel.ml_per_barrel * max_purchase

                    # Add max quantity amount of barrel to purchase list
                    barrel_purchase_list.append({
                        "sku": barrel.sku,
                        "quantity": max_purchase,
                    })
            
    return barrel_purchase_list