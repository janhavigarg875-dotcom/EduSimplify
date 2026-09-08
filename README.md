# EduSimplify — AI-Powered Course Content Simplification Agent

> **AICTE 2026 Internship Project — Problem Statement No. 24**
> Course Content Simplification Agent

EduSimplify is a web application that uses **IBM Granite** (via IBM watsonx.ai) to help students understand complex academic content. Paste any textbook paragraph, lecture note, or topic description and get instant simplifications, key points, definitions, examples, summaries, practice questions, and follow-up Q&A — in English or Hindi.

---

## Features

| # | Feature | Description |
|---|---|---|
| 1 | **Simplify** | Re-explains content in plain language for the chosen difficulty level |
| 2 | **Key Points** | Extracts 5–7 most important points as a numbered list |
| 3 | **Explain Terms** | Identifies and defines difficult technical terms |
| 4 | **Real-World Example** | Gives a relatable analogy or real-world example |
| 5 | **Short Summary** | Writes a 3–5 sentence plain-language summary |
| 6 | **Practice Questions** | Generates 5 practice questions with answers |
| 7 | **Follow-Up Q&A** | Answers a specific question the student types about the content |

**Difficulty levels:** Beginner · Intermediate · Advanced  
**Output languages:** English · Hindi (हिंदी)

---

## Project Structure

```
EduSimplify/
├── app.py                  # Flask application entry point
├── .env                    # Your IBM credentials (NOT committed to git)
├── .env.example            # Credential template — safe to commit
├── .gitignore
├── requirements.txt
├── README.md
│
├── services/
│   ├── __init__.py
│   └── granite_service.py  # IBM watsonx.ai client + all prompt builders
│
├── routes/
│   ├── __init__.py
│   └── api.py              # Flask Blueprint with all /api/* endpoints
│
├── static/
│   ├── index.html          # Single-page frontend
│   ├── style.css           # Styling
│   └── app.js              # Frontend logic (Vanilla JS)
│
└── tests/
    ├── __init__.py
    └── test_api.py         # pytest test suite
```

---

## How It Works

```
Student's browser
      │
      │  POST /api/<feature>
      │  { content, level, language }
      ▼
Flask route (routes/api.py)
      │
      │  validate input
      │  build prompt
      ▼
granite_service.py
      │
      │  IBM IAM auth (WATSONX_APIKEY from .env)
      │  POST /ml/v1/text/generation
      ▼
IBM watsonx.ai
IBM Granite 4 (ibm/granite-4-h-small)
      │
      │  generated_text
      ▼
Flask → JSON response → Browser displays result
```

---

## IBM Services Used

| Service | Details |
|---|---|
| **IBM watsonx.ai** | Hosts the Granite model; Lite tier (free) |
| **IBM Granite** | Model ID: `ibm/granite-4-h-small` |
| **IBM IAM** | Authentication for the API key |

---

## Prerequisites

- Python **3.10** or newer
- An **IBM Cloud** account (free — [cloud.ibm.com](https://cloud.ibm.com))
- A **watsonx.ai** project (Lite tier is free)
- Your IBM Cloud **API key** and **Project ID**

---

## Setup Instructions

### 1. Get IBM Credentials

1. Log in to [cloud.ibm.com](https://cloud.ibm.com) and create a **watsonx.ai** service instance (Lite).
2. Open your watsonx.ai project → **Manage** tab → copy the **Project ID**.
3. Go to **Manage → Access (IAM) → API keys** → create a new API key and copy it.

### 2. Clone and Install

```bash
git clone <your-repo-url>
cd EduSimplify

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` and fill in your real values:

```
WATSONX_APIKEY=your-actual-api-key
WATSONX_PROJECT_ID=your-actual-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

> ⚠️ **Never share or commit your `.env` file.** It is listed in `.gitignore`.

### 4. Run the Application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

### 5. Run Tests

```bash
pytest tests/ -v
```

---

## API Reference

All endpoints accept `POST` requests with a JSON body and return:

```json
{ "result": "...generated text...", "error": null }
```

On error:

```json
{ "result": null, "error": "...error message..." }
```

| Endpoint | Required fields | Optional |
|---|---|---|
| `POST /api/simplify` | `content`, `level`, `language` | — |
| `POST /api/keypoints` | `content`, `level`, `language` | — |
| `POST /api/terms` | `content`, `level`, `language` | — |
| `POST /api/example` | `content`, `level`, `language` | — |
| `POST /api/summary` | `content`, `level`, `language` | — |
| `POST /api/questions` | `content`, `level`, `language` | — |
| `POST /api/followup` | `content`, `level`, `language`, `question` | — |

**Valid values:**
- `level`: `"Beginner"`, `"Intermediate"`, `"Advanced"`
- `language`: `"English"`, `"Hindi"`
- `content`: 1 – 5000 characters

---

## Security Notes

- The IBM API key (`WATSONX_APIKEY`) is **only ever read on the server**, inside `services/granite_service.py`.
- It is **never** included in any API response, log message, frontend code, or documentation.
- `.env` is in `.gitignore` — it will never be accidentally committed.
- `.env.example` contains only placeholder values — it is safe to commit.

---

## Known Limitations

- Input is capped at **5,000 characters** to stay within the Granite Lite token budget.
- Hindi output quality depends on the Granite model's training; technical terms may still appear in English.
- No conversation history — each request is independent (the full content is re-sent each time).
- Requires an active internet connection to reach IBM watsonx.ai.
- IBM Lite tier has rate limits; the app will return an error if the limit is hit.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI model | IBM Granite 4 (`ibm/granite-4-h-small`) via IBM watsonx.ai |
| Backend | Python 3.10+ · Flask 3 · ibm-watsonx-ai SDK |
| Frontend | HTML5 · CSS3 · Vanilla JavaScript (ES2020) |
| Config | python-dotenv |
| Tests | pytest |

---

*Built with IBM Bob for AICTE 2026 Internship — Problem Statement No. 24.*
