import os
import sys
import json
import uuid
import asyncio
from typing import Optional

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import HOST, PORT, UPLOAD_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE
from engine.ingestion import DocumentProcessor
from engine.rag_pipeline import RAGChain
from engine.study import StudyToolsGenerator

# Init server app
app = FastAPI(
    title="CogniLearn",
    description="Intelligent Document Intelligence & Study Platform",
    version="1.0.0",
)

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processor instance
doc_processor = DocumentProcessor(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    min_chunk_size=MIN_CHUNK_SIZE
)

rag_chain = None
study_tools = None
doc_registry = {}

def get_rag_chain():
    # Cache RAGChain loader
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain()
    return rag_chain

def get_study_tools():
    # Cache StudyTools loader
    global study_tools
    if study_tools is None:
        study_tools = StudyToolsGenerator()
    return study_tools

# Static assets mapping
static_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/frontend", StaticFiles(directory=static_dir), name="frontend")

@app.get("/", response_class=HTMLResponse)
async def root():
    # Render index html
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    # Upload parse document
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in doc_processor.SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported extension: {ext}")

    file_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    try:
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        doc_info = doc_processor.process_file(save_path, file.filename)
        chain = get_rag_chain()
        chain.add_document(doc_info)

        doc_registry[doc_info["doc_id"]] = {
            "doc_id": doc_info["doc_id"],
            "filename": doc_info["filename"],
            "file_type": doc_info["file_type"],
            "total_chars": doc_info["total_chars"],
            "num_chunks": doc_info["num_chunks"],
            "uploaded_at": doc_info["uploaded_at"],
            "file_path": save_path,
            "raw_text": doc_info["raw_text"][:10000],
        }

        return JSONResponse({
            "status": "success",
            "document": {
                "doc_id": doc_info["doc_id"],
                "filename": doc_info["filename"],
                "file_type": doc_info["file_type"],
                "total_chars": doc_info["total_chars"],
                "num_chunks": doc_info["num_chunks"],
                "uploaded_at": doc_info["uploaded_at"],
            }
        })
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {e}")

@app.get("/api/documents")
async def list_documents():
    # List uploaded metadata
    docs = list(doc_registry.values())
    clean_docs = [{k: v for k, v in d.items() if k not in ("raw_text", "file_path")} for d in docs]
    return {"documents": clean_docs}

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    # Remove registered document
    if doc_id not in doc_registry:
        raise HTTPException(404, "Document missing")

    chain = get_rag_chain()
    chain.delete_document(doc_id)

    file_path = doc_registry[doc_id].get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    del doc_registry[doc_id]
    return {"status": "deleted", "doc_id": doc_id}

@app.post("/api/query")
async def query_documents(body: dict):
    # Standard query executor
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(400, "Question required")
    
    session_id = body.get("session_id", "default")
    chain = get_rag_chain()
    return chain.query(question, session_id)

@app.post("/api/flashcards")
async def generate_flashcards(body: dict):
    # Generate cards list
    doc_id = body.get("doc_id")
    num_cards = body.get("num_cards", 10)
    topic = body.get("topic", "")

    text = _get_document_text(doc_id)
    tools = get_study_tools()
    cards = tools.generate_flashcards(text, num_cards, topic)
    return {"flashcards": cards}

@app.post("/api/quiz")
async def generate_quiz(body: dict):
    # Generate quiz options
    doc_id = body.get("doc_id")
    num_questions = body.get("num_questions", 5)
    topic = body.get("topic", "")

    text = _get_document_text(doc_id)
    tools = get_study_tools()
    quiz = tools.generate_quiz(text, num_questions, topic)
    return {"quiz": quiz}

@app.post("/api/mindmap")
async def generate_mindmap(body: dict):
    # Generate graph nodes
    doc_id = body.get("doc_id")
    topic = body.get("topic", "")

    text = _get_document_text(doc_id)
    tools = get_study_tools()
    mindmap = tools.generate_mindmap(text, topic)
    return {"mindmap": mindmap}

@app.get("/api/analytics")
async def get_analytics():
    # Fetch usage metrics
    chain = get_rag_chain()
    analytics = chain.get_analytics()
    analytics["total_documents"] = len(doc_registry)
    analytics["total_chunks"] = chain.vector_store.count()
    return analytics

def _get_document_text(doc_id: Optional[str] = None) -> str:
    # Retrieve raw text
    if doc_id and doc_id in doc_registry:
        return doc_registry[doc_id].get("raw_text", "")
    elif doc_registry:
        return "\n\n---\n\n".join(d.get("raw_text", "") for d in doc_registry.values())
    else:
        raise HTTPException(400, "Documents required")

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    # Stream socket connection
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            question = msg.get("question", "").strip()

            if not question:
                await websocket.send_text(json.dumps({"type": "error", "data": "Empty question"}))
                continue

            chain = get_rag_chain()
            if chain.vector_store.count() == 0:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": "No documents uploaded."
                }))
                continue

            try:
                for chunk in chain.stream_query(question, session_id):
                    await websocket.send_text(chunk)
                    await asyncio.sleep(0.01)
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "data": str(e)}))
    except WebSocketDisconnect:
        print(f"📡 Disconnected: {session_id}")
    except Exception as e:
        print(f"⚠️ Socket error: {e}")

if __name__ == "__main__":
    # Start uvicorn server
    print("🧠 CogniLearn — Starting server...")
    print(f"🌐 Open http://localhost:{PORT} in your browser")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
