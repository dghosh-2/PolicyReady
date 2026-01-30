# PolicyReady

Healthcare compliance audit tool that analyzes audit questionnaires against a policy database using AI-powered keyword extraction and evidence matching.

## Features

- Upload PDF audit questionnaires with compliance questions
- AI extracts keywords from questions using GPT-4
- Keyword-based search against indexed policy documents
- GPT-4 evaluates each question with evidence from matching policies
- Results show MET/NOT_MET/PARTIAL status with verbatim evidence quotes

## Tech Stack

- **Frontend**: Next.js 16 with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python)
- **Search**: Inverted keyword index (JSON)
- **LLM**: OpenAI GPT-4o with structured outputs

## Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd PolicyReady
```

2. Install dependencies:
```bash
# Install root dependencies (concurrently)
npm install

# Install frontend dependencies
cd frontend && npm install && cd ..

# Create Python virtual environment and install backend dependencies
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

3. Set up environment variables:
```bash
# Create .env file in project root
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

4. Build the policy index (one-time):
```bash
cd backend
source venv/bin/activate
python scripts/build_index.py
```

## Running the Application

Start both frontend and backend:
```bash
npm run dev
```

Or run them separately:
```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev
```

Access the app at http://localhost:3000

## API Endpoints

- `GET /` - Health check
- `GET /policies` - List all policy folders
- `GET /policies/{folder}` - List files in a folder
- `GET /index/stats` - Get index statistics
- `POST /analyze` - Analyze uploaded PDF questionnaire
- `POST /analyze/text` - Analyze questions provided as JSON array

## Project Structure

```
PolicyReady/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes
│   │   ├── models.py         # Pydantic models
│   │   ├── services/
│   │   │   ├── pdf_parser.py # PDF text extraction
│   │   │   ├── indexer.py    # Index builder
│   │   │   ├── search.py     # Keyword search
│   │   │   └── llm.py        # GPT-4 integration
│   │   └── index_data/       # Generated index
│   ├── scripts/
│   │   └── build_index.py    # Index build script
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   └── lib/api.ts        # API client
│   └── package.json
├── Public Policies/          # Policy PDF database
├── .env                      # Environment variables
└── package.json              # Root package.json
```

## How It Works

1. **Indexing**: All PDFs in `Public Policies/` are parsed, chunked, and indexed with keywords
2. **Question Extraction**: Uploaded PDF is parsed, questions (ending with "?") are extracted
3. **Keyword Extraction**: GPT-4 identifies search keywords for each question
4. **Search**: Keywords are matched against the inverted index to find relevant chunks
5. **Answer Generation**: GPT-4 evaluates each question against matched evidence
6. **Results**: Structured output with MET/NOT_MET status and verbatim evidence quotes

## Deployment

For Vercel deployment:
- Frontend deploys as standard Next.js app
- Backend can be converted to Vercel serverless functions
- Index data should be stored in Vercel Blob Storage or similar

## License

MIT
