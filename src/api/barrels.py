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

    #TESTED AND WORKS V2.05

    # Grab Initial Table
    initial_query = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()

    # Grab current ML / Gold value
    num_of_red_ml = first_row.num_red_ml
    num_of_green_ml = first_row.num_green_ml
    num_of_blue_ml = first_row.num_blue_ml
    current_gold = first_row.gold

    # Looping through receieved barrels and adjusting values to eventually update SupaBase data
    for barrel in barrels_delivered:
        # Update Gold Amount
        current_gold -= barrel.price * barrel.quantity
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
    update_global_inventory = f"""
        UPDATE global_inventory 
        SET 
            num_green_ml = {num_of_green_ml},
            num_red_ml = {num_of_red_ml},
            num_blue_ml = {num_of_blue_ml},
            gold = {current_gold}
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(update_global_inventory))

    return "OK"

def ml_per_gold(barrel):
    return barrel.ml_per_barrel / barrel.price

def find_max_purchasable_amount(barrel, current_gold):
    max_purchasable_amount = 1  # At least one barrel can be purchased
    for i in range(2, barrel.quantity + 1):
        quantity_price = barrel.price * i
        if current_gold >= quantity_price:
            max_purchasable_amount = i
        else:
            break
    return max_purchasable_amount


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    # TESTED AND WORKS FOR NOW V2.05

    # Grab current gold and gold benchmark
    initial_query = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()

    current_gold = first_row.gold
    gold_benchmark = first_row.gold_benchmark

    # Potion Benchmarks
    red_benchmark = first_row.red_potion_benchmark
    green_benchmark = first_row.green_potion_benchmark
    # blue_benchmark = first_row.blue_potion_benchmark
    # num_of_red_ml = first_row.num_red_ml
    # num_of_green_ml = first_row.num_green_ml
    # num_of_blue_ml = first_row.num_blue_ml

    select_red = """
    SELECT * 
    FROM potions_table 
    WHERE red = 100
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_red))
        red_potion_row = result.fetchone()

    if red_potion_row:
        red_potion_quantity = red_potion_row.quantity
    else:
        red_potion_quantity = 0
    
    select_green = """
    SELECT * 
    FROM potions_table 
    WHERE green = 100
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_green))
        green_potion_row = result.fetchone()

    if green_potion_row:
        green_potion_quantity = green_potion_row.quantity
    else:
        green_potion_quantity = 0

    select_blue = """
    SELECT * 
    FROM potions_table 
    WHERE blue = 100
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_blue))
        blue_potion_row = result.fetchone()

    if blue_potion_row:
        blue_potion_quantity = blue_potion_row.quantity
    else:
        blue_potion_quantity = 0
    
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
            if barrel.potion_type[1] == 1 and current_gold >= barrel.price and "MINI" not in barrel.sku:
                # Acquire max amount of said barrel
                max_purchase = find_max_purchasable_amount(barrel, current_gold)

                # Update Gold
                current_gold -= barrel.price * max_purchase
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
                if barrel.potion_type[0] == 1 and current_gold >= barrel.price and "MINI" not in barrel.sku:
                    # Acquire max amount of said barrel & Update Gold
                    max_purchase = find_max_purchasable_amount(barrel, current_gold)
                    current_gold -= barrel.price * max_purchase

                    # Add max quantity amount of barrel to purchase list
                    barrel_purchase_list.append({
                        "sku": barrel.sku,
                        "quantity": max_purchase,
                    })
        else:
            # Purchase Max Amount of blue barrels
            for barrel in sorted_wholesale_catalog:
                # Check if barrel is blue
                if barrel.potion_type[2] == 1 and current_gold >= barrel.price and "MINI" not in barrel.sku:
                    # Acquire max amount of said barrel & Update Gold
                    max_purchase = find_max_purchasable_amount(barrel, current_gold)
                    current_gold -= barrel.price * max_purchase

                    # Add max quantity amount of barrel to purchase list
                    barrel_purchase_list.append({
                        "sku": barrel.sku,
                        "quantity": max_purchase,
                    })
            
    return barrel_purchase_list
