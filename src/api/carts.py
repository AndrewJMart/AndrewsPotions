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
    #TESTED AND WORKS V3.01

    insert_cart_row = """
    INSERT INTO carts (customer_name, character_class, level) 
    VALUES(:customer_name, :character_class, :level) returning cart_id
    """
    # Execute the SQL statement with parameter binding
    with db.engine.begin() as connection:
        cart_id = connection.execute(sqlalchemy.text(insert_cart_row), 
                                     {
                                      "customer_name": new_cart.customer_name, 
                                      "character_class": new_cart.character_class,
                                      "level": new_cart.level
                                      }).scalar_one()
    return {"cart_id": cart_id}

class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    #TESTED AND WORKS V3.01

    metadata_obj = sqlalchemy.MetaData()
    potions_table = sqlalchemy.Table("potions_table", metadata_obj, autoload_with=db.engine)
    cart_items = sqlalchemy.Table("cart_items", metadata_obj, autoload_with=db.engine)

    with db.engine.begin() as connection:
        # Grab cost per potion
        result = connection.execute(
        sqlalchemy.select(potions_table).where(potions_table.c.item_sku == item_sku)
        )
        potion_cost = result.fetchone().price

        # Insert Item Quantity Along With Item_SKU and Cart_ID
        cart_items_insert = [{
                            'cart_id': cart_id, 
                            'item_sku': item_sku, 
                            'quantity': cart_item.quantity,
                            'cost_per_potion': potion_cost
                            }]
        
        connection.execute(
            sqlalchemy.insert(cart_items), cart_items_insert
            )

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    #Tested and works V3.01

    metadata_obj = sqlalchemy.MetaData()
    cart_items = sqlalchemy.Table("cart_items", metadata_obj, autoload_with=db.engine)
    potion_ledger = sqlalchemy.Table("potion_ledger", metadata_obj, autoload_with=db.engine)
    transactions = sqlalchemy.Table("transactions", metadata_obj, autoload_with=db.engine)

    # Grab all items from cart_id from cart_items table
    with db.engine.begin() as connection:
        result = connection.execute(
        sqlalchemy.select(cart_items).where(cart_items.c.cart_id == cart_id)
        )
        all_rows = result.fetchall()
        transaction_gold = 0  
        Potion_Ledger_Insert_List = []

        for row in all_rows:
            # Update Potion Count in potions_ledger
            ledger_row = {
                'item_sku': row.item_sku, 
                'quantity': row.quantity
                          }
            Potion_Ledger_Insert_List.append(ledger_row)
            
            # Sum up gold from transaction
            transaction_gold += row.quantity * row.cost_per_potion

        connection.execute(
            sqlalchemy.insert(potion_ledger), Potion_Ledger_Insert_List
            )

        insert_cart_transaction = [{
            'gold': transaction_gold,
            'red_ml': 0,
            'green_ml': 0,
            'blue_ml': 0,
            'dark_ml': 0
        }]
        connection.execute(
            sqlalchemy.insert(transactions), insert_cart_transaction
            )

    return "OK"
