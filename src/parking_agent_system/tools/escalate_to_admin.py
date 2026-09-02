from langchain_core.tools import tool

def build_escalate_to_admin_tool():
    @tool
    def escalate_to_admin(reservation_id: str) -> str:
        """
        Notifies the admin team that a reservation is pending their approval.
        Call this immediately after make_parking_reservation succeeds, passing the reservation ID.
        The human admin will review and approve or refuse via the admin chat interface.
        """
        return (
            f"Reservation {reservation_id} has been queued for admin review. "
            f"Please inform the user their booking is pending approval from the admin team."
        )

    return escalate_to_admin
