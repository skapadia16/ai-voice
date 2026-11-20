import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_community.document_loaders import TextLoader, PyPDFLoader
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from backend.app.config import settings

class RAGService:
    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self.db_dir = Path(settings.VECTOR_DB_DIR)
        self._embeddings = None
        self._vector_store = None
        
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.db_dir.mkdir(parents=True, exist_ok=True)

    @property
    def embeddings(self):
        """Lazy load embeddings model."""
        if self._embeddings is None:
            print("[RAG] Loading HuggingFace Embeddings (all-MiniLM-L6-v2)...")
            try:
                import socket
                socket.create_connection(("huggingface.co", 443), timeout=1.0)
            except OSError:
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"

            self._embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"}
            )
            print("[RAG] Embeddings loaded successfully.")
        return self._embeddings

    @property
    def vector_store(self):
        """Get or initialize Chroma vector store."""
        if self._vector_store is None:
            if (self.db_dir / "chroma.sqlite3").exists():
                print("[RAG] Loading existing ChromaDB from disk...")
                self._vector_store = Chroma(
                    persist_directory=str(self.db_dir),
                    embedding_function=self.embeddings
                )
            else:
                self.reindex_all_documents()
        return self._vector_store

    def get_indexed_documents(self) -> List[Dict[str, Any]]:
        """List all documents currently in the documents folder."""
        docs = []
        for file in self.docs_dir.iterdir():
            if file.is_file() and file.suffix.lower() in [".pdf", ".txt", ".md"]:
                docs.append({
                    "filename": file.name,
                    "size_bytes": file.stat().st_size,
                    "extension": file.suffix.lower()
                })
        return docs

    def load_document(self, file_path: Path):
        """Loads a single PDF or text file."""
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            loader = PyPDFLoader(str(file_path))
            return loader.load()
        elif ext in [".txt", ".md"]:
            loader = TextLoader(str(file_path), encoding="utf-8")
            return loader.load()
        return []

    def reindex_all_documents(self) -> int:
        """Re-indexes all documents present in the documents directory."""
        print("[RAG] Scanning documents folder for indexing...")
        all_docs = []
        for file in self.docs_dir.iterdir():
            if file.is_file() and file.suffix.lower() in [".pdf", ".txt", ".md"]:
                try:
                    docs = self.load_document(file)
                    for d in docs:
                        d.metadata["source_file"] = file.name
                    all_docs.extend(docs)
                except Exception as e:
                    print(f"[RAG] Error loading {file.name}: {e}")

        if not all_docs:
            print("[RAG] No documents to index. Clearing vector store.")
            self._vector_store = None
            return 0

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=60)
        chunks = splitter.split_documents(all_docs)
        print(f"[RAG] Created {len(chunks)} chunks from {len(all_docs)} documents.")

        self._vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.db_dir)
        )
        print("[RAG] ChromaDB updated and persisted successfully.")
        return len(chunks)

    def add_document(self, file_path: Path) -> int:
        """Add and index a new uploaded file into the knowledge base."""
        docs = self.load_document(file_path)
        if not docs:
            return 0

        for d in docs:
            d.metadata["source_file"] = file_path.name

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=60)
        chunks = splitter.split_documents(docs)

        if self._vector_store is None:
            self._vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=str(self.db_dir)
            )
        else:
            self._vector_store.add_documents(chunks)
        
        return len(chunks)

    def delete_document(self, filename: str) -> bool:
        """Delete a document file and rebuild the vector store."""
        target_file = self.docs_dir / filename
        if target_file.exists():
            target_file.unlink()
            if (self.db_dir / "chroma.sqlite3").exists():
                try:
                    shutil.rmtree(str(self.db_dir))
                    self.db_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"Error resetting DB dir: {e}")
            self._vector_store = None
            self.reindex_all_documents()
            return True
        return False

    def _generate_answer_with_llm(self, query: str, context: str) -> Optional[str]:
        """Try to synthesize answer using available LLM API (Groq, OpenAI)."""
        prompt = (
            "Aap ek helpful aur concise voice assistant hain.\n"
            "Diye gaye Documents Context ke aadhar par user ke sawaal ka seedha aur saral uttar 2-3 sentences mein dein.\n"
            "Agar context mein uttar nahi hai toh saaf kahein ki document mein yeh jaankari nahi mili.\n\n"
            f"Context:\n{context}\n\n"
            f"User Question: {query}\n"
            "Voice Answer:"
        )

        if settings.GROQ_API_KEY:
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "You are a concise voice assistant. Reply in clear Hindi or Hinglish."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[RAG] Groq error: {e}")

        if settings.OPENAI_API_KEY:
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 150
                }
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[RAG] OpenAI error: {e}")

        return None

    def query_rag(self, user_query: str, k: int = 3) -> Dict[str, Any]:
        """
        RAG query pipeline:
        1. Search top-k context chunks from ChromaDB
        2. Synthesize conversational voice answer via LLM or extractive summarizer
        3. Return answer + sources
        """
        if not user_query or not user_query.strip():
            return {
                "answer": "Kripya apna sawaal poochein.",
                "sources": [],
                "context": ""
            }

        vs = self.vector_store
        if vs is None:
            return {
                "answer": "Knowledge base mein abhi koi documents nahi hain. Kripya pehle PDF ya text document upload karein.",
                "sources": [],
                "context": ""
            }

        results = vs.similarity_search_with_score(user_query, k=k)
        if not results:
            return {
                "answer": "Aapke sawaal se juda koi bhi document context nahi mila.",
                "sources": [],
                "context": ""
            }

        context_chunks = []
        sources = []
        for doc, score in results:
            content = doc.page_content.strip()
            source_file = doc.metadata.get("source_file", "unknown")
            page = doc.metadata.get("page", None)
            context_chunks.append(content)
            
            source_info = {"file": source_file, "score": round(float(score), 4)}
            if page is not None:
                source_info["page"] = page + 1
            if source_info not in sources:
                sources.append(source_info)

        combined_context = "\n\n".join(context_chunks)

        llm_answer = self._generate_answer_with_llm(user_query, combined_context)
        if llm_answer:
            answer = llm_answer
        else:
            top_chunk = context_chunks[0].replace("\n", " ")
            sentences = [s.strip() for s in top_chunk.split(".") if len(s.strip()) > 15]
            if sentences:
                selected = ". ".join(sentences[:2]) + "."
                answer = f"Document ke anusaar: {selected}"
            else:
                answer = f"Document ke anusaar: {top_chunk[:250]}..."

        return {
            "query": user_query,
            "answer": answer,
            "sources": sources,
            "context": combined_context[:1000]
        }

rag_service = RAGService()
