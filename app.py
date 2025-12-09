import os
import uuid
import shutil
import json
import re
import time
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber
from pypdf import PdfReader  # Free Fallback
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GEMINI SETUP ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.5-flash')

SESSIONS: Dict[str, Dict[str, Any]] = {}

# --- MODELS ---
class AnalyzeRequest(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    session_id: str
    query: str

class RewriteRequest(BaseModel):
    clause_text: str

# --- UTILS ---

def clean_text(text: str) -> str:
    """Removes asterisks, bolding, and extra whitespace."""
    return text.replace("**", "").replace("*", "").strip()

def ocr_via_gemini(file_path: str, mime_type="application/pdf") -> str:
    """
    COST ALERT: This consumes API credits. 
    Only runs if local extraction completely fails.
    """
    print("⚠️ Local extraction failed (0 text found). Triggering Gemini Cloud OCR...")
    try:
        uploaded_file = genai.upload_file(file_path, mime_type=mime_type)
        
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)

        prompt = "Transcribe the full text from this document exactly as it appears. Output raw text only."
        response = model.generate_content([uploaded_file, prompt])
        
        return response.text
    except Exception as e:
        print(f"Gemini OCR Failed: {e}")
        return ""

def extract_text_from_pdf(file_path: str) -> str:
    """
    3-Layer Extraction Logic to SAVE API CREDITS:
    1. Try pdfplumber (Local/Free)
    2. Try pypdf (Local/Free)
    3. Gemini OCR (Cloud/Paid) - Only if 1 & 2 fail.
    """
    full_text = ""
    
    # --- LAYER 1: pdfplumber ---
    print("Trying Layer 1: pdfplumber...")
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text(x_tolerance=2, y_tolerance=3)
                    if text:
                        full_text += text + "\n"
                    # Log progress for debugging
                    if i % 5 == 0: print(f"  Processed page {i+1}...") 
                except Exception as e:
                    print(f"  Skipping page {i+1} due to error: {e}")
    except Exception as e:
        print(f"Layer 1 crash: {e}")

    # Verification
    if len(full_text.strip()) > 50:
        print("✅ Layer 1 Success. Using local PDF text.")
        return full_text

    # --- LAYER 2: pypdf ---
    print("Layer 1 yielded no text. Trying Layer 2: pypdf...")
    full_text = "" 
    try:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            except Exception:
                pass
    except Exception:
        pass

    if len(full_text.strip()) > 50:
        print("✅ Layer 2 Success.")
        return full_text

    # --- LAYER 3: Gemini OCR ---
    print("❌ Layers 1 & 2 failed (Scanned Document). Using Layer 3: Gemini OCR.")
    return ocr_via_gemini(file_path)

@app.get("/")
def home():
    return {"status": "Backend is running"}

@app.post("/upload")
def upload_contract(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # This logic now protects your API Key
    contract_text = extract_text_from_pdf(file_path)

    if not contract_text or len(contract_text) < 10:
         raise HTTPException(status_code=400, detail="Could not extract text. PDF is blank/corrupted and OCR failed.")

    SESSIONS[session_id] = {
        "contract_text": contract_text,
        "chat_history": [],
        "filename": file.filename
    }
    
    return {"session_id": session_id, "message": "File processed"}

@app.post("/analyze")
def analyze_risks(request: AnalyzeRequest):
    session = SESSIONS.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    prompt = f"""
    You are an expert Legal AI. Analyze the contract text below.
    
    INSTRUCTIONS:
    1. Identify the TOP 3 SUBSTANTIAL LEGAL RISKS.
    2. STRICTLY IGNORE OCR errors, typos, or "Lega l" spacing issues. DO NOT report these as risks.
    3. Detect the language. Output in the SAME language.
    4. Return ONLY valid JSON. No Markdown (*).
    
    Format:
    {{
        "risks": [
            {{
                "clause_title": "Short Title",
                "original_text": "Corrected quote from text",
                "risk_explanation": "Concise legal explanation"
            }}
        ]
    }}
    
    Contract:
    {session['contract_text'][:40000]}
    """

    try:
        response = model.generate_content(prompt)
        text_out = response.text.strip().replace("```json", "").replace("```", "")
        text_out = clean_text(text_out)
        return {"risks": text_out}
    except Exception:
        return {"risks": '{"risks": []}'}

@app.post("/chat")
def chat(request: ChatRequest):
    session = SESSIONS.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    context = f"""
    You are a legal assistant. 
    1. Answer based on the contract context below.
    2. Do NOT use markdown (*).
    3. Ignore OCR errors in the text.
    
    Contract context:
    {session['contract_text'][:20000]}
    """
    
    full_prompt = f"{context}\n\nUser Question: {request.query}"
    
    response = model.generate_content(full_prompt)
    clean_response = clean_text(response.text)
    
    session['chat_history'].append({"role": "user", "content": request.query})
    session['chat_history'].append({"role": "ai", "content": clean_response})
    
    return {"response": clean_response}

@app.post("/rewrite")
def rewrite_clause(request: RewriteRequest):
    prompt = f"""
    Act as a senior lawyer. Rewrite this clause to be favorable to the Client.
    
    RULES:
    1. Output ONLY the rewritten paragraph.
    2. Use professional legal language.
    3. No Markdown.
    
    Original Clause:
    "{request.clause_text}"
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned = clean_text(response.text)
        return {"rewritten": cleaned}
    except Exception:
        raise HTTPException(status_code=500, detail="Rewrite failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)