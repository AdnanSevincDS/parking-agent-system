from datetime import datetime
from pathlib import Path
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from parking_agent_system.data_layer.sql_manager import ParkingDatabase

OUTPUT_FILE = Path("data/confirmed_reservations.txt")

mcp = FastMCP("parking-mcp", port=8001)

@mcp.tool()
def write_confirmed_reservation(reservation_id: str) -> str:
    """Write an approved reservation to the confirmed reservations log.
    Call this immediately after approving a reservation, not on refusal.
    """
    try:
        reservation_id = UUID(reservation_id)
    except ValueError:
        return f"Invalid reservation ID: {reservation_id}"
    
    db = ParkingDatabase()
    reservation = db.get_reservation(reservation_id)

    if not reservation:
        return f"Reservation ID {reservation_id} not found."
    
    if reservation["status"] != "approved":
        return f"Reservation ID {reservation_id} is not approved."

    name = f"{reservation['customer_name']} {reservation['customer_surname']}"
    car = reservation["car_number"]
    period = f"{reservation['reservation_start']} to {reservation['reservation_end']}"
    approved_at = datetime.now().strftime("%d-%m-%Y %H:%M")

    line = f"{name} | {car} | {period} | {approved_at}\n"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("a") as f:
        f.write(line)
    
    return f"Reservation {reservation_id} written to confirmed reservations log."

if __name__ == "__main__":
    mcp.run(transport="sse")


