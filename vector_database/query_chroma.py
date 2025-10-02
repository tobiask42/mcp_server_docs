from typing import Any
from chromadb import PersistentClient
from chromadb.api import ClientAPI
from definitions.custom_enums import Names
from pathlib import Path
from definitions import constants
from config.settings import AppSettings, get_settings
from loguru import logger

settings: AppSettings = get_settings()

def query_db(query: str,n_res: int = settings.CHROMA_N_RESULTS) -> Any:
    base_dir = Path(__file__).resolve().parents[1]
    database_path = base_dir / constants.VECTOR_DATABASE / constants.VECTOR_DATABASE_DATA
    client: ClientAPI = PersistentClient(path=database_path)
    if settings.CHROMA_USE_GPU:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        import onnxruntime as ort # type: ignore
        PREFERRED = settings.ONNX_PREFERRED_PROVIDERS
        logger.info(f"Using ONNXRuntime for Query with preferred providers: {PREFERRED}")
        ef = ONNXMiniLM_L6_V2(preferred_providers=PREFERRED)
        collection = client.get_collection(name=Names.VECTOR_DATABASE_COLLECTION, embedding_function=ef) # type: ignore
    else:
        logger.info("Using default embedding function (SentenceTransformer) for Query on CPU.")
        ef = ONNXMiniLM_L6_V2() # type: ignore
        collection = client.get_collection(name=Names.VECTOR_DATABASE_COLLECTION, embedding_function=ef) # type: ignore
    results = collection.query(
        query_texts=[query],
        n_results=n_res
    )
    if len(results) ==0:
        logger.warning("Query returned no results.")
    else:
        logger.info(f"Query returned {len(results['ids'][0])} results.")
    return results