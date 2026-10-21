# Project Dependency Map

This map shows the repository's application, package, test, build, and CI dependencies. It is based on the source imports, `backend/requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`, and `.gitlab-ci.yml` as of 2026-08-10.

```mermaid
flowchart LR
  browser["Browser"]

  subgraph frontend["Frontend"]
    main["main.tsx"]
    app["App.tsx"]
    api["api.ts"]
    status["status.ts"]
    types["types.ts"]

    main --> app
    app --> api
    app --> status
    app --> types
    api --> types
    status --> types
  end

  subgraph frontendPackages["Frontend packages"]
    react["react 19"]
    reactDom["react-dom 19"]
    vite["vite 7"]
    reactPlugin["@vitejs/plugin-react 5"]
    typescript["typescript 5.9"]
    vitest["vitest 3"]
    testingLibrary["@testing-library/react 16"]
    jestDom["@testing-library/jest-dom 6"]
    jsdom["jsdom 26"]
    reactTypes["@types/react + @types/react-dom"]

    reactDom --> react
    reactPlugin --> vite
    vitest --> vite
    testingLibrary --> react
    testingLibrary --> reactDom
    jestDom --> vitest
    reactTypes --> typescript
  end

  subgraph backend["Backend"]
    uvicorn["uvicorn[standard] 0.34"]
    routes["app/main.py"]
    ticketStore["app/tickets.py"]
    models["app/models.py"]

    uvicorn --> routes
    routes --> ticketStore
    routes --> models
    ticketStore --> models
  end

  subgraph backendPackages["Backend packages"]
    fastapi["fastapi 0.115.6"]
    pydantic["pydantic (transitive; directly imported)"]
    starlette["starlette (transitive)"]
    pytest["pytest 8.3.4"]
    httpx["httpx 0.27.2"]
    uvicornExtras["uvicorn standard extras (transitive, unlocked)"]

    fastapi --> pydantic
    fastapi --> starlette
    uvicorn --> uvicornExtras
    starlette --> httpx
  end

  subgraph tests["Tests"]
    frontendTests["App.test.tsx + status.test.ts"]
    backendTests["test_tickets_api.py"]
  end

  subgraph ci["GitLab CI"]
    backendJob["python:3.12 / backend_tests"]
    frontendJob["node:20 / frontend_tests"]
    buildJob["node:20 / frontend_build"]
    evidenceJob["alpine:3.20 + git / bug_fix_evidence"]
    evidenceScript["check_bug_fix_evidence.sh"]

    evidenceJob --> evidenceScript
  end

  browser --> main
  main --> react
  main --> reactDom
  app --> react
  api -- "GET /api/tickets over HTTP" --> routes
  routes --> fastapi
  models --> pydantic

  frontendTests -.-> app
  frontendTests -.-> status
  frontendTests -.-> vitest
  frontendTests -.-> testingLibrary
  frontendTests -.-> jestDom
  frontendTests -.-> jsdom
  backendTests -.-> routes
  backendTests -.-> pytest
  backendTests -.-> httpx

  buildJob -.-> vite
  buildJob -.-> reactPlugin
  buildJob -.-> typescript
  frontendJob -.-> frontendTests
  backendJob -.-> backendTests

  classDef appNode fill:#e7f0ff,stroke:#2563eb,color:#172554
  classDef packageNode fill:#f3e8ff,stroke:#9333ea,color:#3b0764
  classDef testNode fill:#fef3c7,stroke:#d97706,color:#451a03
  classDef ciNode fill:#dcfce7,stroke:#16a34a,color:#052e16
  class main,app,api,status,types,routes,ticketStore,models,uvicorn appNode
  class react,reactDom,vite,reactPlugin,typescript,vitest,testingLibrary,jestDom,jsdom,reactTypes,fastapi,pydantic,starlette,pytest,httpx,uvicornExtras packageNode
  class frontendTests,backendTests testNode
  class backendJob,frontendJob,buildJob,evidenceJob,evidenceScript ciNode
```

Solid arrows represent runtime or source-import dependencies. Dotted arrows represent test, build, or CI dependencies. The HTTP arrow is the frontend/backend contract; its base URL defaults to `http://localhost:8000` and can be overridden with `VITE_API_BASE_URL`.

## Direct Dependency Inventory

| Area | Purpose | Direct dependencies |
| --- | --- | --- |
| Frontend runtime | Browser UI | `react`, `react-dom` |
| Frontend build | Bundling, JSX transform, type checking | `vite`, `@vitejs/plugin-react`, `typescript` |
| Frontend test | Test runner, DOM environment, rendering assertions, types | `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@types/react`, `@types/react-dom` |
| Backend runtime | API, ASGI server | `fastapi`, `uvicorn[standard]` |
| Backend test | Test runner and HTTP client support | `pytest`, `httpx` |
| CI images/tools | Pipeline execution | `python:3.12`, `node:20`, `alpine:3.20`, `git` |

## Dependency Notes

- `pydantic` is imported directly by `backend/app/models.py`, but it is only installed transitively through FastAPI. Declaring it directly would make that source-level dependency explicit.
- `vite`, `@vitejs/plugin-react`, and `typescript` are build-time tools, although they currently live under `dependencies` rather than `devDependencies` in `frontend/package.json`.
- The frontend lockfile contains 209 resolved packages beyond the root project. The diagram intentionally collapses those transitive implementation details into their direct parents.
- Backend dependencies are version-pinned at the top level, but there is no backend lockfile, so transitive versions can change on a fresh install.
- Browser-native `fetch` and `Intl.DateTimeFormat` are platform APIs, not installed packages.

## Sources of Truth

- Backend packages: `backend/requirements.txt`
- Backend pytest configuration: `backend/pyproject.toml`
- Frontend direct packages and scripts: `frontend/package.json`
- Frontend resolved dependency tree: `frontend/package-lock.json`
- Pipeline dependencies: `.gitlab-ci.yml`
