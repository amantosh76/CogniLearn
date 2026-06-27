import os
import re
import csv
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict

class DocumentChunk:
    def __init__(self, text: str, metadata: Dict):
        # Chunk fields initialization
        self.id = str(uuid.uuid4())
        self.text = text
        self.metadata = metadata

    def to_dict(self) -> Dict:
        # Format properties dict
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
        }

class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, min_chunk_size: int = 50):
        # Init processor config
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def process_file(self, file_path: str, original_filename: str = None) -> Dict:
        # Ingest document file
        if original_filename is None:
            original_filename = os.path.basename(file_path)
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError("Unsupported extension")
        
        raw_text = self._extract_text(file_path, ext)
        if not raw_text.strip():
            raise ValueError("Empty document content")

        doc_id = hashlib.md5(f"{original_filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        chunks = self._recursive_chunk(raw_text, original_filename, doc_id)

        return {
            "doc_id": doc_id,
            "filename": original_filename,
            "file_type": ext.replace(".", "").upper(),
            "total_chars": len(raw_text),
            "num_chunks": len(chunks),
            "chunks": chunks,
            "uploaded_at": datetime.now().isoformat(),
            "raw_text": raw_text,
        }

    def _extract_text(self, file_path: str, ext: str) -> str:
        # Extractor router call
        extractors = {
            ".pdf": self._extract_pdf,
            ".docx": self._extract_docx,
            ".txt": self._extract_txt,
            ".md": self._extract_txt,
            ".csv": self._extract_csv,
        }
        return extractors[ext](file_path)

    def _extract_pdf(self, file_path: str) -> str:
        # Parse PDF text
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(f"[Page {i + 1}]\n{text}")
            return "\n\n".join(pages)
        except Exception as e:
            raise ValueError(f"PDF extraction failed: {e}")

    def _extract_docx(self, file_path: str) -> str:
        # Parse Word text
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = []
            for p in doc.paragraphs:
                if p.text.strip():
                    if p.style.name.startswith("Heading"):
                        level = 1
                        try:
                            level = int(p.style.name.replace("Heading ", "").strip())
                        except ValueError:
                            pass
                        paragraphs.append(f"{'#' * level} {p.text}")
                    else:
                        paragraphs.append(p.text)
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise ValueError(f"DOCX extraction failed: {e}")

    def _extract_txt(self, file_path: str) -> str:
        # Read text file
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Text read failed: {e}")

    def _extract_csv(self, file_path: str) -> str:
        # Parse CSV rows
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                rows = list(reader)
                if not rows:
                    return ""
                headers = rows[0]
                lines = [" | ".join(headers), "-" * 40]
                for r in rows[1:]:
                    parts = [f"{h}: {v}" for h, v in zip(headers, r) if v.strip()]
                    lines.append("; ".join(parts))
                return "\n".join(lines)
        except Exception as e:
            raise ValueError(f"CSV extraction failed: {e}")

    def _recursive_chunk(self, text: str, filename: str, doc_id: str) -> List[DocumentChunk]:
        # Split document text
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        chunks_texts = self._split_recursive(text, separators)
        chunks = []
        offset = 0
        for i, chunk_text in enumerate(chunks_texts):
            if len(chunk_text.strip()) < self.min_chunk_size:
                offset += len(chunk_text)
                continue
            chunk = DocumentChunk(
                text=chunk_text.strip(),
                metadata={
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "char_offset": offset,
                    "char_length": len(chunk_text),
                }
            )
            chunks.append(chunk)
            offset += len(chunk_text)
        return chunks

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        # Recursive text splitter
        if len(text) <= self.chunk_size:
            return [text]
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                result = []
                current = ""
                for part in parts:
                    candidate = current + sep + part if current else part
                    if len(candidate) <= self.chunk_size:
                        current = candidate
                    else:
                        if current:
                            result.append(current)
                        if len(part) > self.chunk_size:
                            remaining = separators[separators.index(sep) + 1:]
                            if remaining:
                                result.extend(self._split_recursive(part, remaining))
                            else:
                                for j in range(0, len(part), self.chunk_size - self.chunk_overlap):
                                    result.append(part[j:j + self.chunk_size])
                        else:
                            current = part
                if current:
                    result.append(current)
                if self.chunk_overlap > 0 and len(result) > 1:
                    result = self._add_overlap(result)
                return result
        result = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            result.append(text[i:i + self.chunk_size])
        return result

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        # Add overlaps helper
        if len(chunks) <= 1:
            return chunks
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-self.chunk_overlap:]
            overlapped.append(tail + chunks[i])
        return overlapped
