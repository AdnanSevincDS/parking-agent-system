"""One-time setup script: initialise SQLite schema and ingest static parking data into Milvus."""
from parking_agent_system.data_layer.sql_manager import ParkingDatabase
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore


def main() -> None:
    print("Initialising SQLite schema...")
    ParkingDatabase().initialize_schema()
    print("Done.")

    print("Ingesting static parking data into Milvus...")
    count = ParkingVectorStore().ingest_static_information()
    print(f"Done — {count} chunks ingested.")


if __name__ == "__main__":
    main()
