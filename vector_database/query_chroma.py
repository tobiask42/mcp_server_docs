from typing import Any
from chromadb import PersistentClient
from chromadb.api import ClientAPI
from definitions.custom_enums import Names
from pathlib import Path
from definitions import constants

def query_db(query: str,n_res: int = 3) -> Any:
    base_dir = Path(__file__).resolve().parents[1]
    database_path = base_dir / constants.VECTOR_DATABASE / constants.VECTOR_DATABASE_DATA
    client: ClientAPI = PersistentClient(path=database_path)
    collection = client.get_collection(name=Names.VECTOR_DATABASE_COLLECTION)
    results = collection.query(
        query_texts=[query],
        n_results=n_res
    )
    return results