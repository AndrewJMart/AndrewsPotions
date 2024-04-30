from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from sqlalchemy import func

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

    print(f"SEARCH PAGE: {search_page}")

    # Determine Which Column To Sort By (And How)
    if sort_col is search_sort_options.customer_name:
        order_by = db.search_orders_view.c.customer_name
    elif sort_col is search_sort_options.item_sku:
        order_by = db.search_orders_view.c.item_sku
    elif sort_col is search_sort_options.line_item_total:
        order_by = db.search_orders_view.c.line_item_total
    else:
        order_by = db.search_orders_view.c.time_stamp

    if sort_order is search_sort_order.asc:
        order_by = sqlalchemy.asc(order_by)
    else:
        order_by = sqlalchemy.desc(order_by)

    # Determine Search Page

    # Total Number Of Rows
    total_row_query = """
                      SELECT COUNT(*) as total_rows 
                      FROM search_orders_view
                      """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(total_row_query))
        total_rows = result.total_rows


    if search_page != "":
        search_page = 0
        previous_page = ""
        #Determine If Next Page Is Present
        if 5 * search_page < total_rows:
            next_page = str(search_page + 1)
        else:
            next_page = ""

    else:
        search_page = int(search_page)
        previous_page = str(max(int(search_page) - 1, 0))
        #Determine If Next Page Is Present
        if 5 * search_page < total_rows:
            next_page = str(search_page + 1)
        else:
            next_page = ""

    stmt = (
        sqlalchemy.select(
            db.search_orders_view.c.cart_item_id,
            db.search_orders_view.c.item_sku,
            db.search_orders_view.c.customer_name,
            db.search_orders_view.c.line_item_total,
            db.search_orders_view.c.time_stamp,
        )
        .limit(5)
        .offset(int(search_page) * 5)
        .order_by(order_by, db.search_orders_view.c.cart_item_id)
    )

    # filter only if name parameter is passed
    if customer_name != "":
        stmt = stmt.where(db.search_orders_view.c.customer_name.ilike(f"%{customer_name}%"))
    
    if potion_sku != "":
        stmt = stmt.where(db.search_orders_view.c.item_sku.ilike(f"%{potion_sku}%"))

    with db.engine.connect() as conn:
        result = conn.execute(stmt)
        line_item_list = []
        for row in result:
            line_item_list.append(
            {
                "line_item_id": row.cart_item_id,
                "item_sku": row.item_sku,
                "customer_name": row.customer_name,
                "line_item_total": row.line_item_total,
                "timestamp": row.time_stamp,
            }
            )

    return {
        "previous": previous_page,
        "next": next_page,
        "results": line_item_list,
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

    #TESTED AND WORKS V4.00
    # Grab Current Tick 
    with db.engine.begin() as connection:
        # Grab Current Tick
        grab_latest_tick =  "SELECT MAX(tick_id) AS max_tick_id FROM ticks"

        result = connection.execute(
        sqlalchemy.text(grab_latest_tick)
        )

        tick_id = result.fetchone().max_tick_id
    
        # Select List Of All Customers Today
        grab_today_customers = f"SELECT visitor_name FROM visits where tick_id = {tick_id}"
        result = connection.execute(sqlalchemy.text(grab_today_customers))

        visitor_list = result.fetchall()

        if visitor_list:
            visitor_name_list = [row.visitor_name for row in result.fetchall()]
        else:
            visitor_name_list = []
        
        insert_visitors_list = []
        
        for visitor in customers:
            if visitor.customer_name not in visitor_name_list:
                # Add visitor to list
                visitor_row = {'visitor_name': visitor.customer_name,
                                'visitor_class': visitor.character_class,
                                'level': visitor.level,
                                'tick_id': tick_id
                                }
                insert_visitors_list.append(visitor_row)

        # Insert All New Customers
        connection.execute(
            sqlalchemy.insert(db.visits_table), insert_visitors_list
            )

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    #TESTED AND WORKS V4.00

    # Insert Cart Row Query
    insert_cart_row = """
    INSERT INTO carts (customer_name, character_class, level, tick_id) 
    VALUES(:customer_name, :character_class, :level, :tick_id) returning cart_id
    """

    # Grab Current Tick
    grab_latest_tick =  "SELECT MAX(tick_id) AS max_tick_id FROM ticks"

    with db.engine.begin() as connection:

        result = connection.execute(
        sqlalchemy.text(grab_latest_tick)
        )

        tick_id = result.fetchone().max_tick_id
    
        cart_id = connection.execute(sqlalchemy.text(insert_cart_row), 
                                     {
                                      "customer_name": new_cart.customer_name, 
                                      "character_class": new_cart.character_class,
                                      "level": new_cart.level,
                                      "tick_id": tick_id
                                      }).scalar_one()

    return {"cart_id": cart_id}

class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    #TESTED AND WORKS V4.00
    with db.engine.begin() as connection:
        # Grab cost per potion
        result = connection.execute(
        sqlalchemy.select(db.potions_table).where(db.potions_table.c.item_sku == item_sku)
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
            sqlalchemy.insert(db.cart_items), cart_items_insert
            )

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    #TESTED AND WORKS V4.00
    # Grab all items from cart_id from cart_items table
    with db.engine.begin() as connection:
        result = connection.execute(
        sqlalchemy.select(db.cart_items).where(db.cart_items.c.cart_id == cart_id)
        )
        all_rows = result.fetchall()
        
        # Grab Current Tick
        grab_latest_tick =  "SELECT MAX(tick_id) AS max_tick_id FROM ticks"

        result = connection.execute(
        sqlalchemy.text(grab_latest_tick)
        )
        tick_id = result.fetchone().max_tick_id
        
        transaction_gold = 0  
        Potion_Ledger_Insert_List = []

        for row in all_rows:
            # Update Potion Count in potions_ledger
            ledger_row = {
                'item_sku': row.item_sku, 
                'quantity': -1 * row.quantity,
                'tick_id': tick_id
                          }
            Potion_Ledger_Insert_List.append(ledger_row)
            
            # Sum up gold from transaction
            transaction_gold += row.quantity * row.cost_per_potion

        connection.execute(
            sqlalchemy.insert(db.potion_ledger), Potion_Ledger_Insert_List
            )

        insert_cart_transaction = [{
            'gold': transaction_gold,
            'red_ml': 0,
            'green_ml': 0,
            'blue_ml': 0,
            'dark_ml': 0,
            'tick_id': tick_id
        }]
        connection.execute(
            sqlalchemy.insert(db.transactions), insert_cart_transaction
            )

    return "OK"
