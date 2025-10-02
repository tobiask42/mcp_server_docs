# Installation
# pip install "chromadb>=0.6" onnxruntime-gpu

import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
import onnxruntime as ort
from onnxruntime import InferenceSession
# Create a dummy session to list available providers
session = InferenceSession("dummy.onnx", providers=ort.get_available_providers())
print("ONNX providers:", session.get_providers())  # sollte 'CUDAExecutionProvider' enthalten
ef = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider"])
ef = ONNXMiniLM_L6_V2(preferred_providers=["CUDAExecutionProvider"])

client = chromadb.PersistentClient(path="chroma_db")
col = client.get_or_create_collection(name="docs", embedding_function=ef)

col.add(ids=["1","2"], documents=["Hallo Welt","GPU Embeddings in Chroma"])
print(col.query(query_texts=["Welt"], n_results=1))
