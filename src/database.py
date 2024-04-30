import os
import dotenv
import sqlalchemy
from src import database as db
from sqlalchemy import create_engine

def database_connection_url():
    dotenv.load_dotenv()

    return os.environ.get("POSTGRES_URI")

engine = create_engine(database_connection_url(), pool_pre_ping=True)

metadata_obj = sqlalchemy.MetaData()
cart = sqlalchemy.Table("carts", metadata_obj, autoload_with= db.engine)
cart_items = sqlalchemy.Table("cart_items", metadata_obj, autoload_with= db.engine)
search_orders_view = sqlalchemy.Table("search_orders_view", metadata_obj, autoload_with= db.engine)
transactions = sqlalchemy.Table("transactions", metadata_obj, autoload_with=db.engine)
potion_ledger = sqlalchemy.Table("potion_ledger", metadata_obj, autoload_with=db.engine)
visits_table = sqlalchemy.Table("visits", metadata_obj, autoload_with=db.engine)
potions_table = sqlalchemy.Table("potions_table", metadata_obj, autoload_with=db.engine)
barrel_tracker = sqlalchemy.Table("barrel_tracker", metadata_obj, autoload_with=db.engine)