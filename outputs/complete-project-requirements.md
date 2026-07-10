# AI-First CRM HCP Module: Complete Project Requirements

## 1. Project Title

AI-First CRM HCP Module - Log Interaction Screen

## 2. Project Objective

Build an AI-first Customer Relationship Management module for life sciences field representatives, focused on logging Healthcare Professional interactions.

The core feature is the Log HCP Interaction screen, where representatives can log interactions using a conversational AI assistant. The AI assistant extracts structured CRM data from natural language and automatically populates a read-only interaction form.

The system must prove that the interaction form is controlled by AI, not by manual user entry.

## 3. Primary User

The primary user is a life sciences field representative.

The representative needs to:

- Log HCP meetings quickly
- Capture discussion details accurately
- Record materials shared
- Record samples distributed
- Capture HCP sentiment
- Add outcomes and follow-up actions
- Avoid spending time manually filling long CRM forms

## 4. Core Functional Requirement

The application must provide a split-screen Log HCP Interaction screen.

Left side:

- Interaction Details form
- Read-only
- Fully controlled by AI output
- User must not manually type into this form

Right side:

- AI assistant chat interface
- User enters natural language prompts here
- AI parses the prompt and updates the left form

The user can log a new interaction or edit an existing interaction only through the AI assistant.

## 5. Critical Assessment Rule

The left-side form must not be manually editable.

All form values must be updated through this flow:

```text
User prompt in AI chat
-> React frontend
-> Redux action
-> FastAPI backend
-> LangGraph agent
-> LangGraph tool
-> Groq LLM
-> Structured JSON response
-> Redux state update
-> Read-only form auto-populates
```

Hard-coding the final interaction logic without the required technologies is not acceptable.

## 6. Required Tech Stack

### Frontend

- React
- Redux Toolkit
- Vite
- JavaScript or TypeScript
- Google Inter font
- CSS modules or standard CSS

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### AI Agent Framework

- LangGraph

### LLM Provider

- Groq

### LLM Models

Primary model:

```text
gemma2-9b-it
```

Optional model for richer context:

```text
llama-3.3-70b-versatile
```

### Database

Use one of:

- PostgreSQL
- MySQL

Recommended option:

```text
PostgreSQL
```

### Environment Variables

```text
GROQ_API_KEY=
DATABASE_URL=
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5173
```

## 7. High-Level Architecture

```text
React UI
  |
  | user prompt + current interaction state
  v
Redux Store
  |
  v
FastAPI Backend
  |
  v
LangGraph Agent
  |
  +--> Log Interaction Tool
  +--> Edit Interaction Tool
  +--> HCP Profile Lookup Tool
  +--> Material Recommendation Tool
  +--> Follow-Up Suggestion Tool
  |
  v
Groq LLM
  |
  v
Structured JSON
  |
  v
FastAPI Response
  |
  v
Redux Update
  |
  v
Read-only Form Auto-Populates
```

## 8. Main Screen Requirement

Screen name:

```text
Log HCP Interaction
```

Layout:

```text
------------------------------------------------------------
| Log HCP Interaction                                      |
------------------------------------------------------------
| Interaction Details Form          | AI Assistant Chat     |
|                                   |                       |
| Read-only fields                  | User prompt input     |
| AI-populated data                 | Chat messages         |
|                                   | Log button            |
------------------------------------------------------------
```

Recommended desktop proportions:

```text
Left panel: 65%
Right panel: 35%
```

Responsive behavior:

- Desktop: split screen
- Tablet: split screen if space allows
- Mobile: stacked panels

## 9. Left Panel: Interaction Details Form

The form must contain these fields:

- HCP Name
- Interaction Type
- Date
- Time
- Attendees
- Topics Discussed
- Materials Shared
- Samples Distributed
- Observed/Inferred HCP Sentiment
- Outcomes
- Follow-up Actions
- AI Suggested Follow-ups

All fields must be:

```text
readOnly
disabled
Redux-controlled
AI-updated
```

There must be no manual user editing of the form.

## 10. Right Panel: AI Assistant Chat

The AI assistant chat must contain:

- Header
- Short subtitle
- Message history
- User prompt input
- Log button
- Loading state
- Error state

Example placeholder:

```text
Describe interaction...
```

Example assistant starter message:

```text
Describe the HCP interaction. Example: Met Dr. Sharma today, discussed Product X efficacy, shared brochure, positive sentiment.
```

## 11. Required User Flows

### Flow 1: Log New Interaction

1. User opens Log HCP Interaction screen.
2. Empty read-only form appears on the left.
3. AI assistant chat appears on the right.
4. User types an interaction description.
5. React stores the user message in Redux.
6. React sends the message and current form state to FastAPI.
7. FastAPI validates the request.
8. FastAPI invokes the LangGraph agent.
9. LangGraph routes the request to the Log Interaction tool.
10. The tool calls Groq using `gemma2-9b-it`.
11. The LLM extracts structured fields.
12. LangGraph validates and merges the response.
13. FastAPI returns updated interaction state.
14. Redux updates the interaction state.
15. The left form auto-populates.

Example user prompt:

```text
Met Dr. Priya Sharma today at 10:30 AM. Discussed Product X efficacy and safety profile. Shared clinical study brochure. She seemed positive and asked for elderly patient data.
```

Expected form update:

```json
{
  "hcpName": "Dr. Priya Sharma",
  "interactionType": "Meeting",
  "date": "2026-07-09",
  "time": "10:30",
  "topicsDiscussed": "Product X efficacy and safety profile",
  "materialsShared": ["Clinical study brochure"],
  "sentiment": "Positive",
  "outcomes": "HCP requested elderly patient data.",
  "followUpActions": ["Send elderly patient data"]
}
```

### Flow 2: Edit Existing Interaction

1. User has an AI-populated form.
2. User types an edit prompt into chat.
3. React sends the edit prompt and current form state to FastAPI.
4. LangGraph routes the request to the Edit Interaction tool.
5. The tool identifies only the fields to update.
6. Existing unchanged fields are preserved.
7. Redux updates the form with the merged state.

Example user prompt:

```text
Change the sentiment to neutral and add Dr. Mehta as an attendee.
```

Expected partial update:

```json
{
  "sentiment": "Neutral",
  "attendees": ["Dr. Mehta"]
}
```

Fields such as HCP name, date, time, topics, and materials must remain unchanged.

### Flow 3: Save Interaction

1. User reviews the AI-populated read-only form.
2. User clicks Save.
3. React sends the current Redux interaction state to FastAPI.
4. FastAPI validates required fields.
6. Data is saved to PostgreSQL or MySQL.
7. Audit log is created.
8. Backend returns success.
9. Interaction appears in the HCP timeline.

## 12. Redux Requirements

Use Redux Toolkit for state management.

Required slices:

```text
interactionSlice
chatSlice
```

### interactionSlice State

```json
{
  "hcpId": null,
  "hcpName": "",
  "interactionType": "",
  "date": "",
  "time": "",
  "attendees": [],
  "topicsDiscussed": "",
  "materialsShared": [],
  "samplesDistributed": [],
  "sentiment": "Unknown",
  "outcomes": "",
  "followUpActions": [],
  "suggestedFollowUps": [],
    "status": "Not checked",
    "warnings": []
  }
}
```

### chatSlice State

```json
{
  "messages": [],
  "isLoading": false,
  "error": null
}
```

### Required Redux Actions

```text
updateInteractionState
mergeInteractionPatch
resetInteraction
setSuggestedFollowUps
addUserMessage
addAssistantMessage
setChatLoading
setChatError
```

## 13. FastAPI Requirements

The backend must expose API endpoints for AI interaction processing and saving CRM data.

### Required Endpoints

```text
POST /api/interaction/agent
POST /api/interaction/save
GET /api/interaction/{interaction_id}
PATCH /api/interaction/{interaction_id}
GET /api/hcps/search
```

### POST /api/interaction/agent

Purpose:

Process a chat prompt through LangGraph and return updated interaction state.

Request:

```json
{
  "message": "Met Dr. Sharma today...",
  "currentInteractionState": {}
}
```

Response:

```json
{
  "assistantMessage": "I logged the interaction and updated the form.",
  "updatedInteractionState": {},
  "toolCalls": [],
}
```

### POST /api/interaction/save

Purpose:

Save the finalized interaction to the database.

Request:

```json
{
  "interaction": {}
}
```

Response:

```json
{
  "interactionId": "INT-1001",
  "status": "saved"
}
```

## 14. LangGraph Agent Requirements

The LangGraph agent manages the AI workflow.

Responsibilities:

- Understand user intent
- Select the correct tool
- Call Groq LLM where needed
- Extract structured interaction data
- Edit existing interaction data
- Preserve unchanged fields
- Recommend follow-ups
- Return structured JSON to the backend

### LangGraph State

```json
{
  "message": "",
  "currentInteractionState": {},
  "intent": "",
  "selectedTool": "",
  "toolResults": {},
  "updatedInteractionState": {},
  "assistantMessage": "",
  "errors": []
}
```

### Agent Flow

```text
START
-> Intent Router
-> Selected Tool
-> State Merge
-> Validation
-> Response Builder
-> END
```

## 15. Required LangGraph Tools

At least five tools must be implemented. This project should implement six.

### Tool 1: Log Interaction

Mandatory.

Purpose:

Parse natural language and create a structured interaction record.

Extract:

- HCP name
- Date
- Time
- Interaction type
- Attendees
- Topics discussed
- Materials shared
- Samples distributed
- Sentiment
- Outcomes
- Follow-up actions

Must use the LLM for:

- Summarization
- Entity extraction
- Sentiment inference
- Follow-up extraction
- Structured JSON generation

### Tool 2: Edit Interaction

Mandatory.

Purpose:

Modify existing form fields based on follow-up prompts.

Rules:

- Update only requested fields
- Preserve all unchanged data
- Never clear fields unless the user explicitly asks
- Return a patch or merged state

### Tool 3: HCP Profile Lookup

Purpose:

Find and enrich HCP details from the CRM database.

Returns:

- HCP ID
- Name
- Specialty
- Territory
- Preferred channel
- Previous product interest

### Tool 4: Material Recommendation

Purpose:

Recommend approved materials based on the topics discussed.

Examples:

- Clinical study brochure
- Safety profile PDF
- Product detail aid
- Patient subgroup analysis

Rules:

- Recommend only approved materials
- Do not invent non-approved content

### Tool 5: Follow-Up Suggestion

Purpose:

Recommend next best actions based on the interaction.

Examples:

- Send clinical data
- Schedule follow-up meeting
- Share approved PDF
- Add HCP to invite list


Purpose:


Checks:

- Missing required fields
- Unapproved materials
- Sample distribution requirements
- HCP restrictions
- Audit trail requirements

Returns:

```json
{
  "status": "Approved",
  "warnings": []
}
```

or:

```json
{
  "status": "Warning",
  "warnings": ["Sample distribution requires quantity and batch number."]
}
```

## 16. Groq LLM Requirements

Use Groq as the LLM provider.

Primary model:

```text
gemma2-9b-it
```

Optional context model:

```text
llama-3.3-70b-versatile
```

The backend must read the API key from:

```text
GROQ_API_KEY
```

The LLM prompt must request structured JSON.

Important instruction:

```text
Do not invent missing information. Use null or empty arrays for missing values.
```

## 17. Database Requirements

Use PostgreSQL or MySQL.

Recommended tables:

```text
users
hcps
interactions
interaction_attendees
interaction_materials
interaction_samples
follow_up_actions
chat_messages
audit_logs
approved_materials
```

### hcps

Stores HCP profile data.

Fields:

```text
id
name
specialty
territory
preferred_channel
created_at
updated_at
```

### interactions

Stores main interaction records.

Fields:

```text
id
hcp_id
interaction_type
interaction_date
interaction_time
topics_discussed
sentiment
outcomes
created_by
created_at
updated_at
```

### interaction_materials

Stores materials shared during the interaction.

Fields:

```text
id
interaction_id
material_id
material_name
created_at
```

### interaction_samples

Stores samples distributed.

Fields:

```text
id
interaction_id
product_name
quantity
batch_number
created_at
```

### follow_up_actions

Stores confirmed follow-up actions.

Fields:

```text
id
interaction_id
action_text
due_date
status
owner_id
created_at
updated_at
```

### chat_messages

Stores chat transcript.

Fields:

```text
id
interaction_id
role
message
created_at
```

### audit_logs

Stores AI and user action history.

Fields:

```text
id
interaction_id
user_id
user_prompt
tool_called
previous_state
new_state
model_used
created_at
```


The system must support auditability because it is designed for a life sciences CRM.

Audit logs must capture:

- User prompt
- Tool called
- Previous state
- New state
- Model used
- Timestamp
- User ID

The system must preserve history of AI-generated changes.

## 19. Validation Rules

Before saving, required fields must include:

```text
HCP Name
Interaction Type
Date
Topics Discussed
```

Sample validation:

```text
If samples are distributed, product name, quantity, and batch number are required.
```

Material validation:

```text
Only approved materials can be saved as shared materials.
```

Edit validation:

```text
Edit Interaction must not overwrite unrelated fields.
```

## 20. UI Acceptance Criteria

The UI is acceptable when:

- Split-screen layout is implemented.
- Left panel contains the interaction form.
- Right panel contains the AI assistant chat.
- Form fields are disabled/read-only.
- Chat input is the only editable interaction input.
- Form values come from Redux state.
- AI responses update the form automatically.
- Save button saves the structured interaction state.
- Loading and error states are visible.
- Inter font is used.
- Design feels like a professional CRM interface.

## 21. Backend Acceptance Criteria

The backend is acceptable when:

- FastAPI app runs successfully.
- `/api/interaction/agent` accepts chat prompts.
- LangGraph is invoked from the backend.
- Tool calls are handled through LangGraph.
- Groq model is called using `GROQ_API_KEY`.
- Responses are structured JSON.
- Invalid input returns useful errors.
- Save endpoint persists interaction data.
- Audit logs are created.

## 22. AI Acceptance Criteria

The AI layer is acceptable when:

- Minimum five LangGraph tools are implemented.
- Log Interaction tool works from natural language.
- Edit Interaction tool updates only requested fields.
- HCP Profile Lookup tool enriches records.
- Material Recommendation tool suggests approved materials.
- Follow-Up Suggestion tool generates next actions.
- Missing information is not invented.
- JSON output is validated before updating Redux.

## 23. Example End-to-End Scenario

User prompt:

```text
Met Dr. Priya Sharma today at 10:30 AM for a meeting. Discussed Product X efficacy and safety profile. Shared the clinical study brochure. She seemed positive and asked for elderly patient data.
```

System behavior:

1. Chat message is stored.
2. FastAPI receives message and current state.
3. LangGraph selects Log Interaction tool.
4. Groq extracts structured data.
5. HCP lookup enriches profile.
6. Follow-up suggestion tool recommends next steps.
8. Redux updates the form.
9. Form displays the interaction.

Expected form state:

```json
{
  "hcpName": "Dr. Priya Sharma",
  "interactionType": "Meeting",
  "date": "2026-07-09",
  "time": "10:30",
  "attendees": [],
  "topicsDiscussed": "Product X efficacy and safety profile",
  "materialsShared": ["Clinical study brochure"],
  "samplesDistributed": [],
  "sentiment": "Positive",
  "outcomes": "HCP requested elderly patient data.",
  "followUpActions": ["Send elderly patient data"],
  "suggestedFollowUps": [
    "Schedule follow-up meeting in 2 weeks",
    "Share Product X elderly patient subgroup analysis"
  ],
    "status": "Approved",
    "warnings": []
  }
}
```

Edit prompt:

```text
Change sentiment to neutral and add Dr. Mehta as an attendee.
```

Expected result:

```json
{
  "sentiment": "Neutral",
  "attendees": ["Dr. Mehta"]
}
```

All other fields remain unchanged.

## 24. Development Phases

### Phase 1: Requirements

Define:

- Objective
- User
- Core functionality
- Tech stack
- Acceptance criteria

### Phase 2: Frontend UI

Build:

- Split-screen layout
- Read-only form
- AI chat panel
- Responsive styling
- Inter font

### Phase 3: Redux State

Build:

- Redux store
- Interaction slice
- Chat slice
- Actions and selectors
- Form controlled by Redux

### Phase 4: FastAPI Backend

Build:

- Backend app
- API endpoints
- Pydantic schemas
- Request validation

### Phase 5: LangGraph Agent

Build:

- Agent state
- Router node
- Tool nodes
- Merge logic
- Response builder

### Phase 6: AI Tools

Build:

- Log Interaction
- Edit Interaction
- HCP Profile Lookup
- Material Recommendation
- Follow-Up Suggestion

### Phase 7: Groq Integration

Build:

- Groq client
- Prompt templates
- JSON extraction
- Model configuration

### Phase 8: Database

Build:

- SQL schema
- ORM models
- Persistence layer
- Audit logging

### Phase 9: Integration

Connect:

- React
- Redux
- FastAPI
- LangGraph
- Groq
- SQL database

### Phase 10: Testing

Test:

- Natural language logging
- Edit prompts
- Read-only form behavior
- Tool routing
- Database save
- Error states

## 25. Final Submission Checklist

```text
React frontend implemented
Redux state management implemented
FastAPI backend implemented
LangGraph agent implemented
Groq integration implemented
gemma2-9b-it used
PostgreSQL or MySQL schema included
Split-screen layout implemented
Left form is read-only
Right chat controls form updates
Minimum five LangGraph tools implemented
Log Interaction tool implemented
Edit Interaction tool implemented
AI extracts form data from natural language
AI edits specific fields without overwriting others
Audit logging included
Interaction save flow included
Professional CRM UI with Inter font
```
