---
name: langchain-agent
description: Use when building, integrating, or testing LangGraph agents inside a FastAPI feature module — defining TypedDict state, @tool with service injection via closures, graph compilation, agent-as-FastAPI-dependency wiring, or testing with FakeListChatModel.
---

# LangChain / LangGraph Agent Pattern

Patterns for building LangGraph agents integrated into FastAPI feature modules.

> Requires `langchain-core`, `langgraph`, and a provider package (`langchain-anthropic`, `langchain-openai`, etc.).
> This codebase's package root is `app/`.
>
> Not set up in this codebase yet — before the first agent:
> - install the packages: `uv add langchain-core langgraph <provider-package>`
> - create `app/core/llm.py` with the `get_primary_model()` / `get_fallback_model()` dependencies used below; each returns a `BaseChatModel` configured from `Settings` (`get_settings()`), built once behind `@lru_cache` like `get_broker`

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
      tools.py        # build_tools() factory with service injection
      prompts.py      # SYSTEM_PROMPT constant
      dependencies.py # ModelRegistry, build_<name>_agent_for_request FastAPI dep
  services/
    service.py        # <Name>AgentService — calls ainvoke, returns schema
  enums.py            # AgentModelName
  schemas.py          # request / response Pydantic models
  routes.py           # thin route handler
```

---

## State

`TypedDict` with LangGraph's `add_messages` reducer — messages accumulate instead of overwrite:

```python
# app/apps/<domain>/agents/<name>/state.py
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

Add extra domain fields (e.g. `org_id: UUID`) only when the agent genuinely must carry them between nodes.

---

## Tools — service injection via closure

LangGraph has no runtime dependency context. Inject services at graph-build time via closure:

```python
# app/apps/<domain>/agents/<name>/tools.py
from langchain_core.tools import BaseTool, tool

from app.apps.<domain>.services.service import RecordsService


def build_tools(service: RecordsService) -> list[BaseTool]:
    @tool
    async def search_records(query: str) -> str:
        """Search records matching the query. Use for questions about specific records or their history."""
        records = await service.search(query)
        return '\n'.join(record.summary for record in records)

    @tool
    async def count_records(filters: str = '') -> int:
        """Count records matching optional filters. Use for 'how many' questions."""
        return await service.count(filters)

    return [search_records, count_records]
```

Rules:
- One `build_tools()` factory per agent — services are captured in the closure.
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
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.apps.<domain>.agents.records_agent.prompts import SYSTEM_PROMPT
from app.apps.<domain>.agents.records_agent.state import AgentState
from app.apps.<domain>.agents.records_agent.tools import build_tools
from app.apps.<domain>.services.service import RecordsService


def build_records_agent(
    model: BaseChatModel,
    service: RecordsService,
) -> CompiledStateGraph:
    tools = build_tools(service)
    model_with_tools = model.bind_tools(tools)

    async def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state['messages']]
        response = await model_with_tools.ainvoke(messages)
        return {'messages': [response]}

    def choose_next_node(state: AgentState) -> str:
        last_message = state['messages'][-1]
        return 'tools' if getattr(last_message, 'tool_calls', None) else END

    graph = StateGraph(AgentState)
    graph.add_node('agent', call_model)
    graph.add_node('tools', ToolNode(tools))
    graph.add_edge(START, 'agent')
    graph.add_conditional_edges('agent', choose_next_node, ['tools', END])
    graph.add_edge('tools', 'agent')
    return graph.compile()
```

---

## Model registry

`AgentModelName` lives in the domain's `enums.py`, never inline: the request schema uses it too, and `dependencies.py` imports the schemas.

```python
# app/apps/<domain>/enums.py
from enum import StrEnum


class AgentModelName(StrEnum):
    PRIMARY = 'primary'
    FALLBACK = 'fallback'
```

```python
# app/apps/<domain>/schemas.py
from pydantic import BaseModel

from app.apps.<domain>.enums import AgentModelName


class RecordsAgentRequest(BaseModel):
    question: str
    model: AgentModelName


class RecordsAgentResponse(BaseModel):
    answer: str
```

```python
# app/apps/<domain>/agents/<name>/dependencies.py
from typing import TypeAlias

from fastapi import Depends
from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from app.apps.<domain>.agents.records_agent.builder import build_records_agent
from app.apps.<domain>.enums import AgentModelName
from app.apps.<domain>.schemas import RecordsAgentRequest
from app.apps.<domain>.services.service import RecordsService
from app.core.llm import get_fallback_model, get_primary_model

ModelRegistry: TypeAlias = dict[AgentModelName, BaseChatModel]


def build_model_registry(
    primary_model: BaseChatModel = Depends(get_primary_model),
    fallback_model: BaseChatModel = Depends(get_fallback_model),
) -> ModelRegistry:
    return {AgentModelName.PRIMARY: primary_model, AgentModelName.FALLBACK: fallback_model}


def build_records_agent_for_request(
    payload: RecordsAgentRequest,
    registry: ModelRegistry = Depends(build_model_registry),
    service: RecordsService = Depends(),
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

from app.apps.<domain>.agents.records_agent.state import AgentState
from app.apps.<domain>.schemas import RecordsAgentRequest, RecordsAgentResponse


class RecordsAgentService:
    async def answer_question(
        self,
        payload: RecordsAgentRequest,
        agent: CompiledStateGraph,
    ) -> RecordsAgentResponse:
        initial_state: AgentState = {
            'messages': [HumanMessage(content=payload.question)]
        }
        final_state = await agent.ainvoke(initial_state)
        last_message = final_state['messages'][-1]
        return RecordsAgentResponse(answer=last_message.content)
```

---

## Agent route

```python
# app/apps/<domain>/routes.py
from fastapi import APIRouter, Depends, status
from langgraph.graph.state import CompiledStateGraph

from app.apps.<domain>.agents.records_agent.dependencies import build_records_agent_for_request
from app.apps.<domain>.schemas import RecordsAgentRequest, RecordsAgentResponse
from app.apps.<domain>.services.service import RecordsAgentService

router = APIRouter()


@router.post('/ask', response_model=RecordsAgentResponse, status_code=status.HTTP_201_CREATED)
async def ask_records_agent(
    payload: RecordsAgentRequest,
    service: RecordsAgentService = Depends(),
    agent: CompiledStateGraph = Depends(build_records_agent_for_request),
) -> RecordsAgentResponse:
    return await service.answer_question(payload, agent)
```

---

## Testing

Use a fake chat model for deterministic responses — never call a real LLM in tests. The model is the only mocked boundary: services, repositories and the DB stay real, and tests go through HTTP (see `testing-rules-styles`).

The stock fakes (`FakeListChatModel`, `FakeMessagesListChatModel`) raise `NotImplementedError` on `bind_tools`, which `build_<name>_agent` always calls. Subclass once in `tests/conftest.py` and expose a fixture that overrides **both** model dependencies, the same way `mock_broker` overrides `get_rabbit_broker`:

```python
# tests/conftest.py
from collections.abc import Sequence
from typing import Self

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

from app.core.llm import get_fallback_model, get_primary_model


class FakeToolChatModel(FakeMessagesListChatModel):
    """Scripted chat model that accepts bind_tools; the stock fakes raise NotImplementedError there."""

    def bind_tools(self, tools: Sequence[object], *, tool_choice: str | None = None, **kwargs: object) -> Self:
        return self


@pytest.fixture
def fake_chat_model(app: FastAPI) -> FakeToolChatModel:
    model = FakeToolChatModel(responses=[])
    override_dependency(app, get_primary_model, lambda: model)
    override_dependency(app, get_fallback_model, lambda: model)
    return model
```

Queue the model's replies in the setup block — `responses` is a flat list, one message per model call:

```python
from langchain_core.messages import AIMessage

from tests.conftest import FakeToolChatModel, TestBaseClientDBClass


class TestAskRecordsAgent(TestBaseClientDBClass):
    async def test_answer_returned_without_tool_call(self, fake_chat_model: FakeToolChatModel) -> None:
        fake_chat_model.responses = [AIMessage(content='No records found.')]

        response = await self.member_client.post('/ask', json={'question': 'Show records', 'model': 'primary'})

        assert response.status_code == 201
        assert response.json() == {'answer': 'No records found.'}
```

To test tool-calling paths, queue an `AIMessage` with `tool_calls` set before the final text response:

```python
fake_chat_model.responses = [
    AIMessage(content='', tool_calls=[{'name': 'search_records', 'args': {'query': 'rock'}, 'id': 'call_1'}]),
    AIMessage(content='Found 3 matching records.'),
]
```

---

## Anti-patterns

| Pattern | Why it fails |
|---|---|
| Import service inside `@tool` at module level | Creates hidden globals; use `build_tools(service)` closure |
| `agent.invoke(...)` (sync) in an async route | Blocks the event loop; always use `await agent.ainvoke(...)` |
| Accessing `AsyncSession` directly from a tool | Tools call services only — repos are the DB layer |
| Building the graph inside the route handler | Breaks DI; build in the `build_<name>_agent_for_request` dependency |
| Storing `CompiledStateGraph` as a singleton | Not thread-safe across requests; build per request |
| System prompt stored in state `messages` | Prepend `SystemMessage` inside `call_model` each turn instead |
| Calling a real LLM in tests | Use the `fake_chat_model` fixture — a `FakeMessagesListChatModel` subclass that accepts `bind_tools` (see Testing) |

## Gotchas

- `add_messages` accumulates — do not include `SystemMessage` in the initial state or it will grow with every turn.
- `ToolNode` matches tool function names exactly to `tool_calls[*].name` — names must be identical.
- `ainvoke` always returns the full final state dict, not just the last message — extract `final_state['messages'][-1]`.
- Provider packages differ: `langchain-anthropic` uses `ChatAnthropic`, `langchain-openai` uses `ChatOpenAI` — both satisfy `BaseChatModel`.