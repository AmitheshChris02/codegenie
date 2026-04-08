# CodeGenie Chat: Current Build Documentation

Last updated: April 7, 2026

## 1. What this application is

CodeGenie Chat is a full-stack streaming chat application.

- Backend: FastAPI + AG-UI protocol events + Strands/AWS Bedrock streaming.
- Frontend: Next.js 14 + TypeScript + Zustand + AG-UI HttpAgent.
- UI protocol: Google A2UI messages for dynamic component rendering.

The app is built so the model can emit structured UI blocks, and the frontend can render them as surfaces while still showing text deltas in the chat transcript.

## 2. Tech stack

### Backend

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic v2
- boto3 (Bedrock runtime)
- strands-agents
- ag-ui-protocol (Python)

### Frontend

- Next.js 14.2
- React 18
- TypeScript 5
- Zustand + Immer
- Tailwind CSS
- @ag-ui/client + @ag-ui/core
- @a2ui/web_core
- Official Google A2UI React renderer bundle (vendored locally in `src/vendor/a2ui-react`)

## 3. Repository layout (important)

There are two `app` directories with different purposes.

- `app/` (repo root): Python backend package.
- `src/app/`: Next.js App Router frontend.

Key backend files:

- `app/main.py`: FastAPI bootstrap, CORS, health check.
- `app/api/endpoints/chat.py`: `POST /chat` streaming endpoint.
- `app/utils/streaming.py`: AG-UI event stream orchestration.
- `app/agents/strands_agent.py`: Strands + Bedrock streaming client.
- `app/agents/a2ui_builder.py`: token parser (`<a2ui>`, `<thinking>`) + fallback repair.
- `app/agents/agui_event_builder.py`: prompt/history shaping + A2UI surface message builder.
- `app/models/ui_protocols.py`: local A2UI/AGUI helper models used in the stream parser.

Key frontend files:

- `src/app/layout.tsx`: global layout/fonts/providers.
- `src/app/providers.tsx`: theme provider.
- `src/app/page.tsx`: redirect to `/chat`.
- `src/app/chat/page.tsx`: chat page entry.
- `src/components/chat/ChatLayout.tsx`: primary runtime orchestration.
- `src/components/chat/MessageList.tsx`: chat block renderer.
- `src/store/chatStore.ts`: conversation/message stream state.
- `src/components/a2ui/registerCustomCatalog.tsx`: default + custom A2UI component registry.
- `src/lib/a2ui-react.tsx`: `@a2ui/react` alias re-export.
- `src/vendor/a2ui-react/index.js`: vendored official Google A2UI React renderer bundle.
- `src/components/ui/*`: custom UI components (Markdown, Code, Diff, Chart, ActionCard, etc.).

## 4. End-to-end runtime flow

## 4.1 User text prompt flow

1. User submits text in `MessageInput`.
2. `ChatLayout` appends a user message to Zustand.
3. `HttpAgent` (`@ag-ui/client`) calls `POST /chat` with `RunAgentInput`.
4. FastAPI endpoint (`/chat`) streams AG-UI events encoded by `EventEncoder`.
5. `chat_event_stream` starts run events and streams model output.
6. Model token stream is parsed by `build_stream_events`:
   - `thinking` events
   - `text_delta` events
   - `a2ui` payload events
7. Backend converts each `A2UIPayload` into official A2UI server messages:
   - first payload: `beginRendering`, then `surfaceUpdate`
   - later payloads: `surfaceUpdate`
8. Backend emits custom AG-UI event:
   - `name = "A2UI_MESSAGES"`
   - `value = { "messages": [ ... ] }`
9. Frontend subscriber handles events:
   - text deltas -> append streamed text
   - custom A2UI messages -> `processMessages(...)` in A2UI provider
   - extracted `surfaceId`s -> appended as `a2ui_surface` blocks
10. `MessageList` renders `A2UIRenderer` for each `a2ui_surface` block.

## 4.2 UI action flow

1. User clicks an action in an A2UI-rendered component.
2. A2UI action is dispatched through provider `onAction`.
3. `ChatLayout` starts a new run with `forwardedProps.a2uiAction`.
4. Backend `build_prompt_and_history(...)` detects the action envelope and creates an action-specific prompt.
5. Agent streams next response, potentially updating surfaces again.

## 5. Backend architecture details

## 5.1 API contract

`POST /chat` currently accepts AG-UI `RunAgentInput` (not the old `ChatRequest`).

- Input type: `ag_ui.core.RunAgentInput`
- Output type: AG-UI event stream (`text/event-stream`) encoded by `ag_ui.encoder.EventEncoder`

## 5.2 Stream parser behavior

`app/agents/a2ui_builder.py` parses model token output incrementally.

- Recognizes `<a2ui> ... </a2ui>` blocks.
- Recognizes `<thinking> ... </thinking>` blocks.
- Handles malformed A2UI JSON with repair logic (especially MarkdownBlock cases).
- Converts plain text into fallback `MarkdownBlock` A2UI payloads so UI still renders.

## 5.3 Surface message builder

`A2UISurfaceMessageBuilder` in `app/agents/agui_event_builder.py` maintains one surface per run.

- Surface id: `surface-{run_id}`
- Root component id: `root`
- Layout: root `Column` with `children.explicitList`
- Each payload appends a new `node-{n}` child component

## 5.4 Agent layer

`BedrockStreamingAgent` in `app/agents/strands_agent.py`:

- Normalizes env vars from `AWS_BEDROCK_*` to standard AWS names.
- Attempts Strands SDK first.
- Falls back to direct Bedrock `converse_stream` token streaming.
- Uses a system prompt that strongly instructs A2UI block output.

## 6. Frontend architecture details

## 6.1 Main runtime

`src/components/chat/ChatLayout.tsx` handles:

- HttpAgent initialization per thread.
- Streaming subscriber callbacks.
- Thinking state toggles.
- Text delta accumulation.
- A2UI custom payload normalization (object/array/string/envelope).
- Surface id extraction and render block insertion.

## 6.2 Message rendering

`MessageList` renders assistant content blocks in this order:

- `thinking` -> `ThinkingIndicator`
- `text` -> `StreamingText` while active, `MarkdownBlock` when done
- `a2ui_surface` -> `A2UIRenderer surfaceId=...`
- `a2ui` -> legacy fallback through `A2UIResolver`

Note: Current primary path is `a2ui_surface` + `A2UIRenderer`.

## 6.3 State model

`chatStore.ts` tracks:

- `messages`
- `conversations`
- `conversationId`
- `isStreaming`
- `currentStreamingId`

Key mutations:

- `startAssistantMessage`
- `appendTextDelta`
- `appendA2UISurface`
- `setThinking`
- `finalizeMessage`
- `reset`

## 7. A2UI catalog in this app

This app loads both:

1. Google default catalog via `initializeDefaultCatalog()`.
2. Custom components registered on top:
   - `MarkdownBlock`
   - `CodeViewer`
   - `DiffViewer`
   - `RechartGraph`
   - `ActionCard`
   - `ThinkingBubble`

Custom registrations are in `src/components/a2ui/registerCustomCatalog.tsx`.

## 8. `@a2ui/react` integration note

The app uses the official Google renderer bundle, but vendored locally.

Why:

- Direct npm install of `@a2ui/react` is blocked in this environment because of a filesystem permission issue creating `node_modules/uc.micro` (a transitive dependency path).

Current workaround:

- Vendored official bundle at `src/vendor/a2ui-react/index.js`.
- Type alias export at `src/lib/a2ui-react.tsx`.
- TS path alias maps `@a2ui/react` to local re-export.
- Webpack alias maps `markdown-it` to local shim (`src/lib/vendor/markdown-it.ts`).

## 9. Markdown checkbox behavior

There are two checkbox behaviors:

1. True A2UI `CheckBox` component nodes (Google catalog) -> interactive via A2UI state model.
2. Markdown task-list checkboxes in `MarkdownBlock` -> now locally interactive in UI via custom renderer state.

Markdown task-list checkbox state is local client UI state only and is not persisted back to backend state.

## 10. Environment variables

Do not commit real secrets. Use your own values in `.env`.

Backend:

- `AWS_REGION` or `AWS_BEDROCK_REGION`
- `AWS_ACCESS_KEY_ID` or `AWS_BEDROCK_ACCESS_KEY`
- `AWS_SECRET_ACCESS_KEY` or `AWS_BEDROCK_SECRET_KEY`
- `BEDROCK_MODEL_ID` (optional)
- `AWS_BEDROCK_INFERENCE_PROFILE_ARN` (optional model fallback)
- `FRONTEND_ORIGIN` (optional CORS origin)

Frontend:

- `NEXT_PUBLIC_API_BASE_URL` (currently expected `http://127.0.0.1:8009`)
- `NEXT_PUBLIC_MODEL_NAME` (badge text only)

## 11. Local development

Install:

```bash
npm install
py -m pip install -r requirements.txt
```

Run backend:

```bash
py -m uvicorn app.main:app --host 127.0.0.1 --port 8009
```

Run frontend:

```bash
npm run dev
```

Open:

- `http://localhost:3000/chat`

## 12. Verification commands

Frontend type check:

```bash
npx tsc --noEmit
```

Backend compile check:

```bash
py -m compileall app
```

Health check:

```bash
GET http://127.0.0.1:8009/health
```

## 13. Known legacy paths in repo

The following files exist from earlier transport/runtime flow and are not the main current path:

- `src/utils/sseClient.ts`
- `src/utils/aguiDispatcher.ts`
- `src/utils/historySerializer.ts`

Current runtime path is AG-UI `HttpAgent` in `ChatLayout.tsx`.

## 14. How to add a new custom A2UI component

1. Build the UI component in `src/components/ui`.
2. Add component name to both protocol models:
   - `app/models/ui_protocols.py`
   - `src/types/protocols.ts`
3. Update backend mapping (if needed) in:
   - `app/agents/agui_event_builder.py` (`a2ui_payload_to_text` and/or payload props)
4. Register renderer in `src/components/a2ui/registerCustomCatalog.tsx`.
5. Ensure model prompt supports emitting that component JSON in `SYSTEM_PROMPT` (`strands_agent.py`).
6. Run checks (`npx tsc --noEmit`, `py -m compileall app`).

## 15. Operational troubleshooting

If A2UI surfaces do not render:

1. Confirm frontend is pointing to the updated backend URL (`NEXT_PUBLIC_API_BASE_URL`).
2. Restart frontend after `.env` changes.
3. Confirm backend `/chat` stream includes `CUSTOM` event `A2UI_MESSAGES`.
4. Confirm payload contains `messages` with `beginRendering` and `surfaceUpdate`.
5. Check for stale backend processes on old ports (commonly `8000`).
