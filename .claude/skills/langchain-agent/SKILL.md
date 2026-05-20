---
name: langchain-agent
description: Use when building, integrating, or testing LangGraph agents inside a FastAPI feature module — defining TypedDict state, @tool with service injection via closures, graph compilation, agent-as-FastAPI-dependency wiring, or testing with FakeListChatModel.
---

# LangChain / LangGraph Agent Pattern

Patterns for building LangGraph agents integrated into FastAPI feature modules.

> Requires `langchain-core`, `langgraph`, and a provider package (`langchain-anthropic`, `langchain-openai`, etc.).
> This codebase's package root is `app/`.

**Related:** `python-code-style`, `fastapi-service`, `testing-rules-styles`.

---

## File layout

```
app/apps/<domain>/
  agents/
    <name>/
      __init__.py
      builder.py      # build_<name>_agent() — graph factory
      state.py        # AgentState TypedDict
      tools.py        # make_tools() factory with service injection
      prompts.py      # SYSTEM_PROMPT constant
      dependencies.py # ModelRegistry, get_<name>_agent FastAPI dep
  services/
    service.py        # <Name>AgentService — calls ainvoke, returns schema
  schemas.py          # request / response Pydantic models
  routes.py           # thin route handler
```

---

## State

`TypedDict` with LangGraph's `add_messages` reducer — messages accumulate instead of overwrite:

```python
# app/apps/<domain>/agents/<name>/state.py
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

Add extra domain fields (e.g. `org_id: UUID`) only when the agent genuinely must carry them between nodes.

---

## Tools — service injection via closure

LangGraph has no runtime dependency context. Inject services at graph-build time via closure:

```python
# app/apps/<domain>/agents/<name>/tools.py
from langchain_core.tools import tool
from app.apps.<domain>.services.service import SomeDomainService


def make_tools(service: SomeDomainService) -> list:
    @tool
    async def search_records(query: str) -> str:
        """Search clinical records matching the query. Use for patient history questions."""
        results = await service.search(query)
        return "\n".join(r.summary for r in results)

    @tool
    async def count_records(filters: str = "") -> int:
        """Count records matching optional filters. Use for 'how many' questions."""
        return await service.count(filters)

    return [search_records, count_records]
```

Rules:
- One `make_tools()` factory per agent — services are captured in the closure.
- Docstring IS the tool description the LLM sees — write it as a clear instruction ending with "Use for…".
- Tools call services only — never access `AsyncSession` or repositories directly.
- Always `async` when the service method is async.

---

## System prompt

```python
# app/apps/<domain>/agents/<name>/prompts.py
SYSTEM_PROMPT = """
You are a read-only assistant.

Rules:
- Use `search_records` for queries about history or specific events.
- Use `count_records` for questions asking how many records match a filter.
- Refuse any request that would modify data — you are read-only.
- Be concise and factual. Do not speculate beyond what the records show.
""".strip()
```

Rules outperform descriptions — "Use X for Y" beats "You can use X if needed".

---

## Graph builder

Pure function: wires model + tools + prompt into a compiled graph. Accepts `BaseChatModel` so any provider can be injected:

```python
# app/apps/<domain>/agents/<name>/builder.py
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.apps.<domain>.services.service import SomeDomainService

from .prompts import SYSTEM_PROMPT
from .state import AgentState
from .tools import make_tools


def build_records_agent(
    model: BaseChatModel,
    service: SomeDomainService,
) -> CompiledStateGraph:
    tools = make_tools(service)
    model_with_tools = model.bind_tools(tools)

    async def call_model(state: AgentState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile()
```

---

## Model registry

```python
# app/apps/<domain>/agents/<name>/dependencies.py
from enum import StrEnum
from typing import TypeAlias

from fastapi import Depends
from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from app.core.llm import get_fallback_model, get_primary_model

from ..schemas import RecordsAgentRequest
from ..services.service import SomeDomainService
from .builder import build_records_agent


class AgentModelName(StrEnum):
    PRIMARY = 'primary'
    FALLBACK = 'fallback'


ModelRegistry: TypeAlias = dict[AgentModelName, BaseChatModel]


def get_model_registry(
    primary: BaseChatModel = Depends(get_primary_model),
    fallback: BaseChatModel = Depends(get_fallback_model),
) -> ModelRegistry:
    return {AgentModelName.PRIMARY: primary, AgentModelName.FALLBACK: fallback}


def get_records_agent(
    payload: RecordsAgentRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    service: SomeDomainService = Depends(),
) -> CompiledStateGraph:
    return build_records_agent(model=registry[payload.model], service=service)
```

`CompiledStateGraph` is **not** shared across requests — a new instance is built per request via `Depends`.

---

## Agent service

Thin service that assembles state, calls `ainvoke`, and returns the response schema:

```python
# app/apps/<domain>/services/service.py  (agent method)
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from app.apps.<domain>.schemas import RecordsAgentRequest, RecordsAgentResponse
from app.apps.<domain>.agents.records_agent.state import AgentState


class RecordsAgentService:
    async def answer(
        self,
        payload: RecordsAgentRequest,
        agent: CompiledStateGraph,
    ) -> RecordsAgentResponse:
        initial_state: AgentState = {
            'messages': [HumanMessage(content=payload.question)]
        }
        result = await agent.ainvoke(initial_state)
        last_message = result['messages'][-1]
        return RecordsAgentResponse(answer=last_message.content)
```

---

## Agent route

```python
# app/apps/<domain>/routes.py
from fastapi import APIRouter, Depends, status
from langgraph.graph.state import CompiledStateGraph

from app.apps.<domain>.agents.records_agent.dependencies import get_records_agent
from app.apps.<domain>.schemas import RecordsAgentRequest, RecordsAgentResponse
from app.apps.<domain>.services.service import RecordsAgentService

router = APIRouter()


@router.post('/ask', response_model=RecordsAgentResponse, status_code=status.HTTP_201_CREATED)
async def ask_records_agent(
    payload: RecordsAgentRequest,
    service: RecordsAgentService = Depends(),
    agent: CompiledStateGraph = Depends(get_records_agent),
) -> RecordsAgentResponse:
    return await service.answer(payload, agent)
```

---

## Testing

Use `FakeListChatModel` for deterministic responses — never call a real LLM in tests:

```python
from langchain_core.messages import HumanMessage
from langchain_community.chat_models.fake import FakeListChatModel

from app.apps.<domain>.agents.records_agent.builder import build_records_agent


async def test_agent_returns_answer(mock_service):
    model = FakeListChatModel(responses=['No records found for this patient.'])
    agent = build_records_agent(model=model, service=mock_service)

    result = await agent.ainvoke({'messages': [HumanMessage(content='Show records')]})
    assert 'No records found' in result['messages'][-1].content
```

To test tool-calling paths, use `FakeMessagesListChatModel` and supply an `AIMessage` with `tool_calls` set before the final text response:

```python
from langchain_core.messages import AIMessage, ToolMessage
from langchain_community.chat_models.fake import FakeMessagesListChatModel

tool_call_msg = AIMessage(
    content='',
    tool_calls=[{'name': 'search_records', 'args': {'query': 'diabetes'}, 'id': 'call_1'}],
)
final_msg = AIMessage(content='Found 3 records about diabetes.')

model = FakeMessagesListChatModel(responses=[[tool_call_msg], [final_msg]])
```

---

## Anti-patterns

| Pattern | Why it fails |
|---|---|
| Import service inside `@tool` at module level | Creates hidden globals; use `make_tools(service)` closure |
| `agent.invoke(...)` (sync) in an async route | Blocks the event loop; always use `await agent.ainvoke(...)` |
| Accessing `AsyncSession` directly from a tool | Tools call services only — repos are the DB layer |
| Building the graph inside the route handler | Breaks DI; build in the `get_<name>_agent` dependency |
| Storing `CompiledStateGraph` as a singleton | Not thread-safe across requests; build per request |
| System prompt stored in state `messages` | Prepend `SystemMessage` inside `call_model` each turn instead |
| Calling a real LLM in tests | Use `FakeListChatModel` or `FakeMessagesListChatModel` |

## Gotchas

- `add_messages` accumulates — do not include `SystemMessage` in the initial state or it will grow with every turn.
- `ToolNode` matches tool function names exactly to `tool_calls[*].name` — names must be identical.
- `ainvoke` always returns the full final state dict, not just the last message — extract `result["messages"][-1]`.
- Provider packages differ: `langchain-anthropic` uses `ChatAnthropic`, `langchain-openai` uses `ChatOpenAI` — both satisfy `BaseChatModel`.