# CodeGenie: AG UI + Google A2UI Integration Documentation

Last updated: April 9, 2026

## 1. Objective

This chat application is designed to be a component-first AI assistant:

- AG UI (CopilotKit) drives the response event stream.
- Google A2UI renders built-in catalog UI components whenever possible.
- Custom components are used when catalog components are not enough.
- Responses prioritize visual and actionable UI over long plain text.

The target behavior is similar to modern AI assistants (ChatGPT, Claude, Gemini) but with stronger structured UI output.

## 2. Current Behavior Requirements

### Response style

- Prefer UI components as the dominant response format.
- Keep text concise and supportive (minimal filler, limited emoji usage).
- Render true tables/charts/cards/checklists/actions instead of plain text lists.
- Use full message width correctly and avoid clipped/misaligned content.

### Context handling

- Follow-up prompts should use thread context.
- Each answer must be generated for the current question only.
- Prior answers should not be duplicated into later responses unless explicitly needed.

## 3. Architecture

## Frontend

- `src/components/chat/ChatLayout.tsx`
  - Chat shell.
  - Handles custom action callbacks from rendered UI.
- `src/components/chat/MessageList.tsx`
  - Renders chat messages.
  - Routes AG UI/A2UI payloads to resolver components.
- `src/components/chat/A2UIResolver.tsx`
  - Resolves and renders A2UI built-ins.
  - Falls back to registered custom components when needed.
- `src/components/a2ui/registerCustomCatalog.tsx`
  - Registers custom catalog components used by fallback/custom responses.
- `src/components/ui/RechartGraph.tsx`
  - Custom chart renderer for bar/line/area/pie-like graph payloads.

## Backend

- `backend/agents/agui_event_builder.py`
  - Normalizes model output into AG UI event stream payloads.
  - Emits component messages and text events in the expected format.
- `backend/utils/streaming.py`
  - Streams events to frontend in order.
- `app/agents/strands_agent.py`
  - Agent orchestration and model/tool execution.

## 4. AG UI Event Strategy

The backend emits a complete run lifecycle so frontend EventStream is meaningful and renderers have enough data.

### Text events

- start text block
- stream text chunks
- end text block

### UI events

Two custom UI channels are supported:

- `A2UI_MESSAGES`: for Google A2UI built-in catalog components.
- `CODEGENIE_COMPONENT`: for custom catalog components (charts, richer cards, advanced widgets).

### Action events (client to server)

- Button/menu/list action clicks create an AG UI-compatible client event payload.
- Payload is routed through the same run flow so actions can produce new structured responses.

## 5. Built-in vs Custom Component Policy

Component selection priority:

1. Use Google A2UI built-in catalog component if it can express the response well.
2. Use custom registered component only if built-in coverage is insufficient.
3. Use plain text as the final fallback.

### Built-in patterns expected in responses

- Text blocks
- Cards/containers
- Lists and list items
- Buttons/action controls
- Inputs (for interactive flows)
- Multiple-choice/question blocks (when schema-compatible)

### Custom patterns

- Recharts visualizations
- Specialized composite cards
- Domain-specific widgets requiring custom layout/logic

## 6. Fixes Applied (Behavioral)

## A. Repeated/combined answers across questions

Problem:

- Q2 returned Q1 answer.
- Q3 returned combined Q1 + Q2 + Q3 content.

Fix intent:

- Reset per-run streaming buffers.
- Build final answer from current run output only.
- Preserve conversation context separately from rendered answer accumulation.

Result:

- Follow-up context is still available, but output is no longer duplicated across turns.

## B. Built-in components not rendering

Problem:

- Payloads degraded to plain text.

Fix intent:

- Normalize payloads to expected A2UI schema structure.
- Ensure resolver receives valid component name + props shape.
- Keep fallback path to custom components explicit.

## C. Action buttons not triggering follow-up

Problem:

- Buttons rendered, but clicks did nothing.

Fix intent:

- Wire action callback from UI renderer back to chat run handler.
- Convert click payload into synthetic AG UI client event.
- Route through normal backend run pipeline.

Result:

- Actionable items are interactive and can generate new responses.

## D. Recharts bars invisible/cut

Problem:

- Chart shell visible, bars invisible or clipped.

Fix intent:

- Enforce deterministic container dimensions.
- Set explicit bar fill colors and stroke defaults.
- Ensure axis/domain/dataKey mapping is correct.
- Avoid overflow clipping in parent containers.

Note:

- HTML/CSS charts may render while Recharts fails if payload keys mismatch (`xKey`, `yKey`, `series`, or `dataKey`).

## E. EventStream table empty in DevTools

Problem:

- Request payload visible but streamed event rows missing.

Fix intent:

- Emit complete AG UI lifecycle events in order.
- Ensure `content-type` and stream framing are correct.
- Flush events continuously during run.

## 7. Content Formatting Standards

To avoid plain-text quality issues:

- Markdown tables must render as tables, not raw text.
- Heading/list spacing must be normalized.
- Avoid excessive emoji.
- Prefer concise, structured language.
- Use full available layout width for assistant content cards.

## 8. Verification Checklist

Use these prompts to validate component-first behavior:

- "Show SAP modules as a bar chart with legend and filters."
- "Create a migration readiness checklist with checkboxes and action buttons."
- "Generate 5 SAP MCQs with selectable options and a submit action."
- "Give a comparison table of ECC vs S/4HANA with recommendation cards."
- "Create a dashboard for plant maintenance KPIs with trend chart + alerts."

Expected outcomes:

- At least one structured component in each response.
- Charts visible and not clipped.
- Actions trigger new responses.
- Follow-up prompts use context without duplicating previous answer text.

## 9. Local Run Commands

Backend:

```bash
python -m backend.main
```

Frontend:

```bash
npm run dev
```

Quick syntax check:

```bash
python -m compileall backend
```

## 10. Troubleshooting

## Built-in component not rendered

- Validate payload matches expected A2UI schema.
- Confirm component type is supported by resolver.
- Check fallback registration in `registerCustomCatalog.tsx`.

## Button click has no effect

- Verify action handler wiring across resolver -> message list -> chat layout.
- Confirm action payload includes required identifiers and parameters.
- Check backend receives action event as a new run input.

## Recharts still invisible

- Confirm chart `data` is non-empty.
- Confirm `xKey`/`yKey` map to actual data fields.
- Ensure explicit bar `fill` is set.
- Check parent container styles for clipping and zero-height issues.

## EventStream empty

- Inspect response headers and stream framing.
- Confirm backend emits incremental AG UI events, not only final payload.

## 11. Design Principle (USP)

The main USP is not plain conversational text. It is structured, interactive, visual AI responses powered by AG UI + A2UI.

Default response strategy should remain:

- UI components first
- Actions second
- Minimal text third

This ensures responses feel productized and task-oriented, not like a generic text bot.
