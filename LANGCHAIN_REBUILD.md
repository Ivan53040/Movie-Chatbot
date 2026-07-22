# LangChain Rebuild

This repo now contains two backend styles:

- Original orchestration: custom Python router in `router.py`
- LangChain orchestration: runnable pipeline in `langchain_orchestrator.py`

## What changed

The original backend does this in regular Python:

1. contextualize follow-up input
2. parse the query
3. choose a route with `if/else`
4. call search functions
5. rank and explain

The LangChain rebuild moves the orchestration itself into LangChain:

1. `RunnableWithMessageHistory` injects conversation history
2. `RunnablePassthrough.assign(...)` builds pipeline state
3. LangChain prompt chains contextualize and parse the message
4. LangChain prompt chain selects the route
5. `RunnableBranch(...)` dispatches to the retrieval path
6. explanation text is attached before the final response is returned

## New files

- `langchain_history_adapter.py`: adapts the SQLite chat memory to LangChain history objects
- `langchain_orchestrator.py`: the new LangChain-first recommendation pipeline
- `langchain_chatbot_service.py`: service wrapper around the LangChain pipeline
- `fastapi_server_langchain.py`: separate FastAPI entrypoint for the new backend
- `start_chatbot_langchain.ps1`: convenience launcher for the LangChain version

## Learning angle

The key difference is not that LangChain replaces search math.

It does not.

The retrieval, filtering, and scoring are still deterministic Python modules. What changed is the application control flow:

- before: Python decides the sequence
- now: LangChain runnables decide the sequence and hold the state

That is the practical version of saying the project is "built with LangChain":

- LangChain owns orchestration
- Python owns domain logic

## How to run the LangChain version

Use:

```powershell
./start_chatbot_langchain.ps1
```

Or run the API directly:

```powershell
python -m uvicorn fastapi_server_langchain:app --host 127.0.0.1 --port 8011
```
