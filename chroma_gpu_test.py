# pip install "chromadb>=0.6" onnxruntime-gpu

import os
import onnxruntime as ort
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# (optional) DLL-Suchpfade lokal setzen – vermeidet aufgeblähten globalen PATH
os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9\bin")
os.add_dll_directory(r"C:\Program Files\NVIDIA\CUDNN\v9.13\bin\12.9")
# Falls du TensorRT wirklich nutzen willst, den lib-Ordner (nicht "bin") hinzufügen:
# os.add_dll_directory(r"C:\Program Files\NVIDIA Corporation\TensorRT-10.x\lib")  # Pfad anpassen

print("Available ORT providers:", ort.get_available_providers())

# Provider EXPLIZIT festlegen (stabiler als "whatever is available")
PREFERRED = ["CUDAExecutionProvider", "CPUExecutionProvider"]
# Wenn du TensorRT nutzen willst und installiert hast:
# PREFERRED = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]

ef = ONNXMiniLM_L6_V2(preferred_providers=PREFERRED)

import chromadb
client = chromadb.PersistentClient(path="chroma_db")
col = client.get_or_create_collection(name="docs", embedding_function=ef)

col.add(ids=["1","2"], documents=["Hallo Welt","GPU Embeddings in Chroma"])
print(col.query(query_texts=["Welt"], n_results=1))
