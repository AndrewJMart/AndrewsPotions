from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

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

@router.get("/audit")
def get_inventory():
    """ """

    #TESTED AND WORKS WITH V2.1
    current_gold = get_current_gold()
    red_ml, green_ml, blue_ml = get_current_ml_totals()
    total_ml = red_ml + green_ml + blue_ml

    #Query Potions Table to grab current amount of potion quantity
    potion_sum_query = "SELECT SUM(quantity) AS total_potions FROM potion_ledger"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(potion_sum_query))
        first_row = result.fetchone()
    
    if first_row:
        total_potions = first_row.total_potions
    else:
        total_potions = 0

    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": current_gold}


# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
