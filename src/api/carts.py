from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """

    #TESTED AND WORKS V2.05

    insert_cart_row = f"""INSERT INTO carts (customer_name, character_class, level) 
    VALUES ('{new_cart.customer_name}', '{new_cart.character_class}', {new_cart.level})"""

    cart_id_query = f"""SELECT * FROM carts 
                        WHERE customer_name = '{new_cart.customer_name}' 
                        AND character_class = '{new_cart.character_class}'
                        AND level = {new_cart.level}
                        ORDER BY cart_id DESC LIMIT 1"""

        # Execute the SQL statement with parameter binding
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(insert_cart_row))
        cart_id = connection.execute(sqlalchemy.text(cart_id_query)).fetchone().cart_id

    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """

    #TESTED AND WORKS V2.05

    # Grab cost per potion
    potion_cost_query = f"""SELECT * FROM potions_table WHERE item_sku = '{item_sku}'"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(potion_cost_query))
        potion_cost = result.fetchone().price

    # Insert Item Quantity Along With Item_SKU and Cart_ID
    new_cart_items_row = f"""INSERT INTO cart_items (cart_id, item_sku, quantity, cost_per_potion) 
                         VALUES ({cart_id}, '{item_sku}', {cart_item.quantity}, {potion_cost})"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(new_cart_items_row))

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    # Grab all items from cart_id from cart_items table
    select_cart_items = f"SELECT * FROM cart_items WHERE cart_id = {cart_id}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_cart_items))
        all_rows = result.fetchall()
    
    for row in all_rows:
        #Grab Current Quantity of item_sku from potions_table
        select_item_sku = f"SELECT * FROM potions_table WHERE item_sku = '{row.item_sku}'"
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text(select_item_sku))
            current_quantity = result.fetchone().quantity
        
        # Update Potion Count in Potions_Table
        update_sku_quantity = f"""UPDATE potions_table SET quantity = {current_quantity - row.quantity}
                             WHERE item_sku = '{row.item_sku}'"""
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text(update_sku_quantity))

    # Grab current gold value
    global_inventory_select = f"SELECT * FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(global_inventory_select))
        current_gold = result.fetchone().gold
    
    # Grab all rows of the cart_items of this cart_id
    cart_item_list = f"SELECT * FROM cart_items WHERE cart_id = {cart_id}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(cart_item_list))
        all_rows = result.fetchall()

    added_gold = 0

    for row in all_rows:
        added_gold += row.quantity * row.cost_per_potion

    update_gold = f"UPDATE global_inventory SET gold = {current_gold + added_gold}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(update_gold))

    return "OK"
