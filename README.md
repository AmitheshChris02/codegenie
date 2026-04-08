# CodeGenie Chat

Production-style chat app with:

- FastAPI backend
- AWS Bedrock (Claude) streaming
- A2UI (`<a2ui>...</a2ui>`) parsing and rendering
- AGUI intent dispatch from UI action buttons
- Next.js 14 + TypeScript + Zustand + Tailwind frontend

## 1. Environment

Backend reads either standard AWS vars or your Bedrock-prefixed vars:

- `AWS_REGION` or `AWS_BEDROCK_REGION`
- `AWS_ACCESS_KEY_ID` or `AWS_BEDROCK_ACCESS_KEY`
- `AWS_SECRET_ACCESS_KEY` or `AWS_BEDROCK_SECRET_KEY`
- `BEDROCK_MODEL_ID` (optional)
- `AWS_BEDROCK_INFERENCE_PROFILE_ARN` (optional fallback for model id)

Frontend optional vars:

- `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`)
- `NEXT_PUBLIC_MODEL_NAME` (badge text only)

## 2. Install

```bash
# frontend
npm install

# backend
py -3 -m pip install -r requirements.txt
```

## 3. Run

Terminal 1 (backend):

```bash
py -3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):

```bash
npm run dev
```

Open `http://localhost:3000/chat`.

## 4. Build Checks

```bash
npm run build
py -3 -m compileall app
```

