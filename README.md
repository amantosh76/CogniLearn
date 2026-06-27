
# 🧠 CogniLearn

### AI-Powered Document Intelligence & Study Lab

> Transform your documents into interactive study decks and get precise, cited answers using advanced hybrid search and re-ranking.

---

## ✨ Key Features

* **📚 Cognitive Study Suite**:
  * Generate interactive flashcards, multiple-choice quizzes, and dynamic visual mind maps.
* **⚡ Dual-Engine Retrieval (RAG)**:
  * Combines semantic vector search (ChromaDB) with lexical keyword matching (BM25) fused via Reciprocal Rank Fusion (RRF) and re-ranked using LLM scores.
* **💬 Real-time Workspace Chat**:
  * Stream answers token-by-token via WebSocket with visual confidence scores and inline document source citations.
* **📊 Dashboard & Document Hub**:
  * Monitor search latency and document metrics on the analytics dashboard while managing PDF, DOCX, TXT, MD, and CSV files in one hub.
* **🎨 Premium Light Interface**:
  * A modern, elegant workspace designed in a sleek Slate and Emerald palette with a clean navigation hub.

---

## 📐 Architecture

**User Query** ➔ **Query Embedding** (`gemini-embedding-001`) ➔ **Hybrid Retrieval** (Semantic Vector Search with ChromaDB + Lexical Keyword Search with BM25) ➔ **Reciprocal Rank Fusion (RRF)** ➔ **LLM Re-Ranking** (`gemini-3.1-flash-lite`) ➔ **Streaming Answer Generation**.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Gemini API Key ([Get one free](https://aistudio.google.com/apikey))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/amantosh76/CogniLearn.git
cd CogniLearn

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
#    Edit .env and replace 'your_gemini_api_key_here' with your key
```

### Run

```bash
python app.py
```

Open **http://localhost:8000** in your browser.

---

## 🗂️ Project Structure

```
CogniLearn/
├── app.py                      # FastAPI server (REST + WebSocket)
├── config.py                   # Configuration & environment
├── requirements.txt            # Python dependencies
├── .env.example                # API key template
├── engine/
│   ├── ingestion.py            # Multi-format parser + recursive chunking
│   ├── vector_store.py         # ChromaDB & vector search interface
│   ├── lexical.py              # BM25 keyword search index
│   ├── fusion.py               # Reciprocal Rank Fusion rank fusion
│   ├── reranker.py             # LLM-based query relevance re-ranking
│   ├── rag_pipeline.py         # RAG execution pipeline orchestrator
│   ├── memory.py               # Multi-turn conversation chat history memory
│   └── study.py                # Flashcard, Quiz, and Mindmap generator
└── frontend/
    ├── index.html              # Main web portal template
    ├── css/
    │   └── styles.css          # Beautiful light-themed stylesheet
    └── js/
        ├── main.js             # UI interactions & mindmap visuals
        └── services.js         # API request backend client integration
```


---

## 🛡️ Tech Stack

- **LLM**: Google Gemini 3.1 Flash Lite (Main Chat) / 3.5 Flash (Study Tools)
- **Embeddings**: Gemini gemini-embedding-001 (3072-dim)
- **Vector Store**: ChromaDB (persistent, local)
- **Backend**: FastAPI + Uvicorn + WebSocket
- **Search**: Hybrid Semantic + BM25 with RRF
- **Frontend**: Vanilla HTML/CSS/JS (no framework)


---

<p align="center">
  Built with 🧠 by CogniLearn
</p>
