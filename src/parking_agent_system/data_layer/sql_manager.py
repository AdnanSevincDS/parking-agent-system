"""SQLite persistence for parking reservation requests."""
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from parking_agent_system.config import settings

PENDING_APPROVAL_STATUS = "pending_approval"

class ParkingDatabase:
    """Manage SQLite storage for parking reservation requests."""

    def __init__(self, data_base_path: Path | None = None) -> None:
        self._database_path = data_base_path or settings.sqlite_db_path

    def _connect(self) -> sqlite3.Connection:
        """Create a SQLite connection with foreign-key enforcement enabled."""
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    
    def initialize_schema(self) -> None:
        """
        Create required tables if they do not exist.
        """
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_requests (
                    reservation_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_surname TEXT NOT NULL,
                    car_number TEXT NOT NULL,
                    reservation_start TEXT NOT NULL,
                    reservation_end TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reservation_requests_status ON reservation_requests (status)"""
            )

    def create_pending_reservation(
        self,
        *,
        conversation_id: UUID,
        customer_name: str,
        customer_surname: str,
        car_number: str,
        reservation_start: datetime,
        reservation_end: datetime,
    ) -> UUID:
        """
        Store a reservation request requiring administrator approval.

        Returns:
            The generated reservation request UUID.

        Important:
            Caller-side validation must ensure reservation_end is after
            reservation_start before calling this method.
        """
        reservation_id = uuid4()
        created_at = datetime.now().astimezone().isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reservation_requests (
                    reservation_id,
                    conversation_id,
                    customer_name,
                    customer_surname,
                    car_number,
                    reservation_start,
                    reservation_end,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                ,
                (
                    str(reservation_id),
                    str(conversation_id),
                    customer_name,
                    customer_surname,
                    car_number,
                    reservation_start.isoformat(),
                    reservation_end.isoformat(),
                    PENDING_APPROVAL_STATUS,
                    created_at,
                ),
            )
        return reservation_id
    def get_reservation(self, reservation_id: UUID) -> dict[str, str] | None:
        """
        Return one reservation record for internal use.

        Do not return this raw dictionary directly from a public API because
        it contains customer PII.
        """
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    reservation_id,
                    conversation_id,
                    customer_name,
                    customer_surname,
                    car_number,
                    reservation_start,
                    reservation_end,
                    status,
                    created_at
                FROM reservation_requests
                WHERE reservation_id = ?
                """,
                (str(reservation_id),),
            ).fetchone()
        return dict(row) if row else None