import json
import re
import time
from typing import List, Dict
import google.generativeai as genai
from config import GEMINI_API_KEY, STUDY_TOOLS_MODEL

MAX_INPUT_CHARS = 2000

class StudyToolsGenerator:
    def __init__(self):
        # Init model connection
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(STUDY_TOOLS_MODEL)
        self.max_retries = 3
        self.base_retry_delay = 15

    def _generate_with_retry(self, prompt: str) -> str:
        # LLM retry logic
        for attempt in range(self.max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                err = str(e).lower()
                is_rate = any(k in err for k in ("429", "quota", "rate", "resource"))
                if is_rate and attempt < self.max_retries - 1:
                    wait = self.base_retry_delay * (attempt + 1)
                    time.sleep(wait)
                else:
                    raise
        return ""

    def generate_flashcards(self, text: str, num_cards: int = 10, topic: str = "") -> List[Dict]:
        # Generate flashcards list
        prompt = f"""You are an expert educator. Based on the following content, generate exactly {num_cards} high-quality flashcards.

Content:
{text[:MAX_INPUT_CHARS]}

{f'Focus on the topic: {topic}' if topic else ''}

Return your response as a JSON array of objects with "front" and "back" keys.
Example format:
[
  {{"front": "What is RAG?", "back": "Retrieval-Augmented Generation combines..."}}
]

IMPORTANT: Return ONLY the JSON array. No markdown, no code blocks, no explanation."""
        try:
            res_text = self._generate_with_retry(prompt)
            return self._parse_json_array(res_text)
        except Exception as e:
            print(f"⚠️ Flashcard error: {e}")
            return [{"front": "Error generating flashcards", "back": str(e)}]

    def generate_quiz(self, text: str, num_questions: int = 5, topic: str = "") -> List[Dict]:
        # Generate quiz list
        prompt = f"""You are an expert educator. Based on the following content, generate exactly {num_questions} multiple-choice questions.

Content:
{text[:MAX_INPUT_CHARS]}

{f'Focus on the topic: {topic}' if topic else ''}

Return your response as a JSON array of objects with:
- "question": text
- "options": 4 options array
- "correct": correct index (0-3)
- "explanation": brief note

IMPORTANT: Return ONLY the JSON array. No markdown, no code blocks, no explanation."""
        try:
            res_text = self._generate_with_retry(prompt)
            return self._parse_json_array(res_text)
        except Exception as e:
            print(f"⚠️ Quiz error: {e}")
            return [{"question": "Error generating quiz", "options": ["N/A"], "correct": 0, "explanation": str(e)}]

    def generate_mindmap(self, text: str, topic: str = "") -> Dict:
        # Generate mindmap graph
        prompt = f"""You are an expert at organizing knowledge. Based on the following content, create a mind map structure.

Content:
{text[:MAX_INPUT_CHARS]}

{f'Focus on the topic: {topic}' if topic else ''}

Return your response as a JSON object with:
- "central": title
- "nodes": array of objects, each with:
  - "id": unique string id
  - "label": short label
  - "parent": parent id (or null)
  - "color": hex color code

IMPORTANT: Return ONLY the JSON object. No markdown, no code blocks, no explanation."""
        try:
            res_text = self._generate_with_retry(prompt)
            return self._parse_json_object(res_text)
        except Exception as e:
            print(f"⚠️ Mindmap error: {e}")
            return {"central": "Error", "nodes": []}

    def _parse_json_array(self, text: str) -> List[Dict]:
        # Parser helper array
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text).strip()
        try:
            res = json.loads(text)
            return res if isinstance(res, list) else [res]
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            return json.loads(match.group()) if match else []

    def _parse_json_object(self, text: str) -> Dict:
        # Parser helper object
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text).strip()
        try:
            res = json.loads(text)
            return res if isinstance(res, dict) else {"central": "Document", "nodes": []}
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return json.loads(match.group()) if match else {"central": "Document", "nodes": []}
