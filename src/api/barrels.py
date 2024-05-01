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

    #TESTED AND WORKS V4.00
    gold = 0
    num_of_red_ml = 0
    num_of_green_ml = 0
    num_of_blue_ml = 0 
    num_of_dark_ml = 0

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
        # Dark Barrel
        elif barrel.potion_type[3] == 1:
            num_of_dark_ml += barrel.ml_per_barrel * barrel.quantity

    # Update the global_inventory to reflect new values
    transaction_insert = [
            {
             'gold': gold,
             'red_ml': num_of_red_ml,
             'green_ml': num_of_green_ml,
             'blue_ml': num_of_blue_ml,
             'dark_ml': num_of_dark_ml
            }
        ]
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.insert(db.transactions), transaction_insert
            )

    return "OK"

def ml_per_gold(barrel):
    return barrel.ml_per_barrel / barrel.price

def get_current_gold():
    #TESTED AND WORKS V4.00
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
    #TESTED AND WORKS V4.00
    with db.engine.begin() as connection:
        # Grab initial gold / Mls
        initial_query = """
        SELECT 
            SUM(red_ml) AS total_red_ml,
            SUM(green_ml) AS total_green_ml,
            SUM(blue_ml) AS total_blue_ml,
            SUM(dark_ml) AS total_dark_ml
        FROM transactions
        """
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

def find_max_purchasable_amount(barrel, current_gold, current_ml, max_ml):
    #TESTED AND WORKS V4.00
    max_purchasable_amount = 1  # At least one barrel can be purchased
    for i in range(2, barrel.quantity + 1):
        quantity_price = barrel.price * i
        quantity_ml = barrel.ml_per_barrel * i
        if current_gold >= quantity_price and current_ml + quantity_ml <= max_ml:
            max_purchasable_amount = i
        else:
            break  # Exit the loop if constraints are violated
    return max_purchasable_amount

def purchase_barrels(catalog, ml_type, current_gold, current_ml, max_ml, mlperbarrelbenchmark):
    #TESTED AND WORKS V4.00
    barrel_purchase_list = []
    for barrel in catalog:
        if barrel.ml_per_barrel >= mlperbarrelbenchmark:
            if barrel.potion_type[ml_type] == 1 and current_gold >= barrel.price and current_ml + barrel.ml_per_barrel <= max_ml:
                # Acquire max amount of said barrel
                max_purchase = find_max_purchasable_amount(barrel, current_gold, current_ml, max_ml)
                current_gold -= barrel.price * max_purchase
                current_ml += barrel.ml_per_barrel * max_purchase
                
                # Add max quantity amount of barrel to purchase list
                barrel_purchase_list.append({
                    "sku": barrel.sku,
                    "quantity": max_purchase,
                })
    
    return barrel_purchase_list

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #TESTED AND WORKS V4.00

    # Benchmarks used for barrel purchasing
    with db.engine.begin() as connection:
        initial_query = "SELECT * FROM global_inventory"
        result = connection.execute(sqlalchemy.text(initial_query))
        first_row = result.fetchone()

        gold_benchmark = first_row.gold_benchmark
        red_ml_benchmark = first_row.red_ml_benchmark
        green_ml_benchmark = first_row.green_ml_benchmark
        blue_ml_benchmark = first_row.blue_ml_benchmark
        dark_ml_benchmark = first_row.dark_ml_benchmark
        red_gold_perc = first_row.red_gold_perc
        green_gold_perc = first_row.green_gold_perc
        blue_gold_perc = first_row.blue_gold_perc
        dark_gold_perc = first_row.dark_gold_perc
        max_total_ml = first_row.max_ml
        mlperbarrelbenchmark = first_row.ml_per_barrel_benchmark


    # Query Current ML / Gold 
    red_ml, green_ml, blue_ml, dark_ml = get_current_ml_totals()
    current_RGBD_ml = red_ml + blue_ml + green_ml + dark_ml
    current_gold = get_current_gold()
    
    # Initialize empty barrel list
    barrel_purchase_list = []

    # Sort catalog on ML_Per_Barrel
    sorted_wholesale_catalog = sorted(wholesale_catalog, key=ml_per_gold, reverse= True)
    print(sorted_wholesale_catalog)

    # Track which barrels are sold at which tick
    with db.engine.begin() as connection:
        # Grab Current Tick
        grab_latest_tick =  "SELECT MAX(tick_id) AS max_tick_id FROM ticks"
        result = connection.execute(sqlalchemy.text(grab_latest_tick))
        tick_id = result.fetchone().max_tick_id

        # Track All Barrels Offered In Catalog
        barrel_tracker_list = []
        for barrel in sorted_wholesale_catalog:
            barrel_tracker_list.append({
                'sku': barrel.sku,
                'ml_per_barrel': barrel.ml_per_barrel,
                'red_barrel': barrel.potion_type[0],
                'green_barrel': barrel.potion_type[1],
                'blue_barrel': barrel.potion_type[2],
                'dark_barrel': barrel.potion_type[3],
                'quantity': barrel.quantity,
                'tick_id': tick_id
            })
        # Insert Barrels Into barrel_tracker table
        connection.execute(
            sqlalchemy.insert(db.barrel_tracker), barrel_tracker_list
            )

    # Benchmark Eval - If Shop is below gold_benchmark (1000) only purchase green barrels
    if current_gold < gold_benchmark:
        #Implement simple selling only green potions
        green_barrels = purchase_barrels(sorted_wholesale_catalog, 1, current_gold,
                                        green_ml, max_total_ml, mlperbarrelbenchmark)
        for barrel in green_barrels:
            barrel_purchase_list.append(barrel)
    else:
        # When shop is above gold benchmark fill in ML categories (30%,30%,30%,10%) Can Scale Later
        remaining_ml = max_total_ml - current_RGBD_ml
        # Dark 
        if dark_ml < remaining_ml * (dark_ml_benchmark/100):
            # Max Amount Of Dark_ML to Purchase
            dark_max_ml = (remaining_ml * (dark_ml_benchmark/100)) - dark_ml
            dark_max_gold = current_gold * (dark_gold_perc/100)
            # Purchase Appropriate Dark Barrels
            dark_barrels = purchase_barrels(sorted_wholesale_catalog, 3, dark_max_gold, 
                                            dark_ml, dark_max_ml, mlperbarrelbenchmark)
            for barrel in dark_barrels:
                barrel_purchase_list.append(barrel)
        # Blue
        if blue_ml < remaining_ml * (blue_ml_benchmark/100):
            # Max Amount Of Blue_ML to Purchase
            blue_max_ml = (remaining_ml * (blue_ml_benchmark/100)) - blue_ml
            blue_max_gold = (current_gold * (blue_gold_perc/100))
            # Purchase Appropriate Blue Barrels
            blue_barrels = purchase_barrels(sorted_wholesale_catalog, 2, blue_max_gold, 
                                            blue_ml, blue_max_ml, mlperbarrelbenchmark)
            for barrel in blue_barrels:
                barrel_purchase_list.append(barrel)
        # Red
        if red_ml < remaining_ml * (red_ml_benchmark/100):
            # Max Amount Of Red_ML to Purchase
            red_max_ml = (remaining_ml * (red_ml_benchmark/100)) - red_ml
            red_max_gold = (current_gold * (red_gold_perc/100))
            # Purchase Appropriate Red Barrels
            red_barrels = purchase_barrels(sorted_wholesale_catalog, 0, red_max_gold, 
                                           red_ml, red_max_ml, mlperbarrelbenchmark)
            for barrel in red_barrels:
                barrel_purchase_list.append(barrel)
        # Green
        if green_ml < remaining_ml * (green_ml_benchmark/100):
            # Max Amount Of Green_ML to Purchase
            green_max_ml = (remaining_ml * (green_ml_benchmark/100)) - green_ml
            green_max_gold = (current_gold * (green_gold_perc/100))
            # Purchase Appropriate Green Barrels
            green_barrels = purchase_barrels(sorted_wholesale_catalog, 1, green_max_gold, 
                                             green_ml, green_max_ml, mlperbarrelbenchmark)
            for barrel in green_barrels:
                barrel_purchase_list.append(barrel)
            
    return barrel_purchase_list