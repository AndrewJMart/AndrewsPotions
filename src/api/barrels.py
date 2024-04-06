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

    num_of_green_ml = first_row[2]
    current_gold = first_row[3]

    # Looping through receieved barrels and adjusting values to eventually update SupaBase data
    for barrel in barrels_delivered:
        if barrel.potion_type[1] == 1:
            num_of_green_ml += barrel.ml_per_barrel * barrel.quantity
            current_gold -= barrel.price * barrel.quantity

    # Now update the global_inventory to reflect actual values

    # Updating Green ML 
    sql_to_execute = f"UPDATE global_inventory SET num_green_ml = {num_of_green_ml}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))

    # Updating Gold
    sql_to_execute = f"UPDATE global_inventory SET gold = {current_gold}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)


    # Query global_inventory for initial table
    sql_to_execute = "SELECT * FROM global_inventory"

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        first_row = result.fetchone()

    number_of_potions = first_row[1]
    current_gold = first_row[3]

    # Basic Logic for developing wholesale purchase plan
    if number_of_potions < 10:
        for barrel in wholesale_catalog:
            if barrel.potion_type[1] == 1 and current_gold - barrel.price >= 0:
                current_gold -= barrel.price
                return [
                            {
                                "sku": barrel.sku,
                                "quantity": 1
                            }
                        ]
    # Old Logic: 
    # else:
    #      return []
    # Note: Now simply don't return anything if not buying barrels
