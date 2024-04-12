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

@router.get("/audit")
def get_inventory():
    """ """

    #TESTED AND WORKS WITH V2.05

    # Query Global_Inventory for current levels of gold and ML
    ml_gold_sum_query = "SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(ml_gold_sum_query))
        fr = result.fetchone()

    current_gold = fr.gold
    current_ml = fr.num_green_ml + fr.num_red_ml + fr.num_blue_ml

    #Query Potions Table to grab current amount of potion quantity
    potion_sum_query = "SELECT SUM(quantity) AS total_potions FROM potions_table"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(potion_sum_query))
        first_row = result.fetchone()
    
    if first_row:
        total_potions = first_row.total_potions
    else:
        total_potions = 0

    return {"number_of_potions": total_potions, "ml_in_barrels": current_ml, "gold": current_gold}


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
