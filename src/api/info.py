from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(timestamp: Timestamp):
    """
    Share current time.
    """
    
    #TESTED AND WORKS V4.00

    insert_tick_row = """
    INSERT INTO ticks (day, hour) 
    VALUES(:day, :hour)
    """
    # Execute the SQL statement with parameter binding
    with db.engine.begin() as connection:
        insert_tick = connection.execute(sqlalchemy.text(insert_tick_row), 
                                     {
                                      "day": timestamp.day, 
                                      "hour": timestamp.hour
                                      })

    return "OK"

