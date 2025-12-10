Here is a comprehensive `README.md` file tailored for your specific backend code. It explains the features, setup, and API endpoints clearly.

````markdown
# Legal AI Backend ⚖️

A high-performance FastAPI backend designed to analyze legal contracts, detect risks, and rewrite clauses using **Google Gemini 2.5 Flash**. This system features a robust **3-Layer PDF Extraction** engine to handle standard and scanned documents efficiently while optimizing API costs.

## 🚀 Key Features

* **Hybrid PDF Extraction:**
    1.  **Layer 1 (Layout):** Uses `pdfplumber` for precise text extraction.
    2.  **Layer 2 (Raw):** Falls back to `pypdf` for raw streams.
    3.  **Layer 3 (OCR):** Automatically triggers **Gemini Cloud OCR** for scanned/image-based PDFs.
* **Strict AI Analysis:** Configured with `temperature=0.0` to ensure factual, deterministic outputs with zero hallucinations.
* **Multilingual Support:** Auto-detects the document language (e.g., Telugu, Hindi, English) and responds in the same language.
* **Cost Optimization:** Only uses paid OCR API calls when local extraction fails.

---

## 🛠️ Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **AI Model:** Google Gemini 2.5 Flash
* **PDF Tools:** `pdfplumber`, `pypdf`
* **Server:** Uvicorn

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/legal-ai-backend.git](https://github.com/your-username/legal-ai-backend.git)
cd legal-ai-backend
````

### 2\. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3\. Install Dependencies

```bash
pip install fastapi uvicorn python-multipart python-dotenv google-generativeai pdfplumber pypdf
```

### 4\. Configure Environment Variables

Create a `.env` file in the root directory and add your Gemini API key:

```ini
GEMINI_API_KEY=your_actual_api_key_here
```

### 5\. Run the Server

```bash
python app.py
```

The server will start at `http://0.0.0.0:5000`.

-----

## 📡 API Endpoints

### 1\. Upload Contract

**POST** `/upload`

  * **Input:** `file` (PDF)
  * **Process:** Handles extraction logic (Layers 1-3).
  * **Output:** `session_id`

### 2\. Risk Analysis

**POST** `/analyze`

  * **Input:** JSON `{ "session_id": "..." }`
  * **Output:** JSON containing Top 3 legal risks, original text quotes, and explanations.

### 3\. Legal Chat Assistant

**POST** `/chat`

  * **Input:** JSON `{ "session_id": "...", "query": "What is the termination notice?" }`
  * **Output:** Plain text answer based strictly on the document context.

### 4\. Clause Rewrite

**POST** `/rewrite`

  * **Input:** JSON `{ "clause_text": "..." }`
  * **Output:** A rewritten version of the clause favorable to the client.

-----

## 🧠 extraction Logic (Cost Saving)

The system protects your API quota using this logic:

1.  **Attempt Local Extraction:** Tries `pdfplumber` first.
2.  **Fallback Extraction:** If Layer 1 fails, tries `pypdf`.
3.  **Validation:** Checks if extracted text length \> 50 characters.
4.  **Cloud OCR:** Only sends the file to Gemini Vision if the previous steps result in empty text (indicating a scanned document).

-----

## 📝 License

This project is open-source and available under the MIT License.

```
```