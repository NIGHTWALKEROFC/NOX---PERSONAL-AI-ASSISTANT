import uuid
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions
from database import get_conn

CHROMA_PATH = "data/chroma"
embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("nox_knowledge", embedding_function=embed_fn)


def _chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _store(text: str, source_type: str, source_name: str) -> str:
    doc_id = str(uuid.uuid4())
    chunks = _chunk(text)
    if not chunks:
        return doc_id

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id, "source_type": source_type, "source_name": source_name} for _ in chunks]
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)

    conn = get_conn()
    conn.execute(
        "INSERT INTO knowledge_meta (id, source_type, source_name) VALUES (?, ?, ?)",
        (doc_id, source_type, source_name)
    )
    conn.commit()
    conn.close()
    return doc_id


def add_text(text: str, name: str = "manual text") -> str:
    return _store(text, "text", name)


def add_pdf(file_bytes: bytes, filename: str) -> str:
    import io
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _store(text, "pdf", filename)


def add_url(url: str) -> str:
    resp = requests.get(url, timeout=15, headers={"User-Agent": "NOX-Assistant"})
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return _store(text, "url", url)


def add_voice_transcript(text: str, name: str = "voice note") -> str:
    return _store(text, "voice", name)


def search(query: str, n_results: int = 4) -> list[str]:
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    return docs


def list_knowledge() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM knowledge_meta ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_knowledge(doc_id: str) -> bool:
    existing = collection.get(where={"doc_id": doc_id})
    ids = existing.get("ids", [])
    if ids:
        collection.delete(ids=ids)

    conn = get_conn()
    conn.execute("DELETE FROM knowledge_meta WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    return True
