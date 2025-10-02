# pip install "chromadb>=0.6" onnxruntime-gpu
import onnxruntime as ort # type: ignore
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# (optional) DLL-Suchpfade lokal setzen – vermeidet aufgeblähten globalen PATH
# Falls du TensorRT wirklich nutzen willst, den lib-Ordner (nicht "bin") hinzufügen:
# os.add_dll_directory(r"C:\Program Files\NVIDIA Corporation\TensorRT-10.x\lib")  # Pfad anpassen

print("Available ORT providers:", ort.get_available_providers()) # type: ignore

# Provider EXPLIZIT festlegen (stabiler als "whatever is available")
PREFERRED = ["CUDAExecutionProvider", "CPUExecutionProvider"]
# Wenn du TensorRT nutzen willst und installiert hast:
# PREFERRED = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]

ef = ONNXMiniLM_L6_V2(preferred_providers=PREFERRED)

import chromadb
client = chromadb.PersistentClient(path="chroma_db")
col = client.get_or_create_collection(name="docs", embedding_function=ef) # type: ignore

col.add(ids=["1","2"], documents=["Hallo Welt","GPU Embeddings in Chroma"])
print(col.query(query_texts=["Welt"], n_results=1))
