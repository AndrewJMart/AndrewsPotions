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

    # Grab Initial Table
    sql_to_execute = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
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

    sql_to_execute = f"""
        UPDATE global_inventory 
        SET 
            num_green_ml = {num_of_green_ml},
            num_red_ml = {num_of_red_ml},
            num_blue_ml = {num_of_blue_ml},
            gold = {current_gold}
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))


    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    # Grab current gold and gold benchmark
    sql_to_execute = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        first_row = result.fetchone()

    current_gold = first_row.gold
    gold_benchmark = first_row.gold_benchmark
    # num_of_red_ml = first_row.num_red_ml
    # num_of_green_ml = first_row.num_green_ml
    # num_of_blue_ml = first_row.num_blue_ml

    sql_to_execute = """
    SELECT * 
    FROM potions_table 
    WHERE red = 100
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        red_potion_quantity = result.fetchone().quantity
    
    sql_to_execute = """
    SELECT * 
    FROM potions_table 
    WHERE green = 100
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        green_potion_quantity = result.fetchone().quantity

    sql_to_execute = """
    SELECT * 
    FROM potions_table 
    WHERE blue = 100
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        blue_potion_quantity = result.fetchone().quantity

    
    # Initialize empty barrel list
    barrel_purchase_list = []

    # Benchmark Eval - If Shop is below gold_benchmark (400) or less than green_potion_benchmark only purchase green barrels
    if current_gold < gold_benchmark or green_potion_quantity < 5:
        
        #Implement simple selling only green potions
        for barrel in wholesale_catalog:    
            # Check if barrel is green
            if barrel.potion_type[1] == 1 and current_gold >= barrel.price:
                
                # Acquire max amount of said barrel
                max_purchasable_amount = 1
                
                for i in range(2, barrel.quantity + 1):
                    quantity_price = barrel.price * i
                    if current_gold > quantity_price:
                        max_purchasable_amount = i
                    else:
                        break
                # Add max quantity amount of barrel to purchase list
                barrel_purchase_list.append({

                    "sku": barrel.sku,
                    "quantity": max_purchasable_amount,

                })
    else:
        #If above gold threshold then begin buying red barrels (if number of red potions is less than ten)
        if red_potion_quantity <= 10:
            #Purchase Max Amount of 
            for barrel in wholesale_catalog:
                # Check if barrel is green
                if barrel.potion_type[0] == 1 and current_gold >= barrel.price:
                    
                    # Acquire max amount of said barrel
                    max_purchasable_amount = 1
                    
                    for i in range(2, barrel.quantity + 1):
                        quantity_price = barrel.price * i
                        if current_gold > quantity_price:
                            max_purchasable_amount = i
                        else:
                            break
                    # Add max quantity amount of barrel to purchase list
                    barrel_purchase_list.append({

                        "sku": barrel.sku,
                        "quantity": max_purchasable_amount,

                    })
        else:
            #Purchase Max Amount of blue barrels
            for barrel in wholesale_catalog:
                # Check if barrel is green
                if barrel.potion_type[2] == 1 and current_gold >= barrel.price:
                    
                    # Acquire max amount of said barrel
                    max_purchasable_amount = 1
                    
                    for i in range(2, barrel.quantity + 1):
                        quantity_price = barrel.price * i
                        if current_gold > quantity_price:
                            max_purchasable_amount = i
                        else:
                            break
                    # Add max quantity amount of barrel to purchase list
                    barrel_purchase_list.append({

                        "sku": barrel.sku,
                        "quantity": max_purchasable_amount,

                    })
            
    return barrel_purchase_list
