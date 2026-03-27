# ModelForge Frontend

React SPA for the ModelForge 3D model generation platform. Provides user authentication, task creation with image upload, real-time task tracking, and 3D model download.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Pages & Routing](#pages--routing)
- [State Management](#state-management)
- [API Integration](#api-integration)
- [Authentication Flow](#authentication-flow)
- [Task Lifecycle](#task-lifecycle)
- [Deployment](#deployment)
- [Future Improvements](#future-improvements)

## Overview

The frontend is a lightweight React SPA built with Vite. It communicates with the Kotlin Service REST API to allow users to:

- **Register and log in** with JWT-based authentication
- **Upload images** (JPG, PNG, WebP) to create 3D generation tasks
- **Monitor task progress** on a filterable, paginated dashboard
- **Download generated 3D models** when processing completes

```mermaid
graph LR
    User([User / Browser])
    FE[Frontend - React SPA]
    NG[Nginx]
    KS[Kotlin Service - REST API]
    PG[(PostgreSQL)]
    MIO[(MinIO / S3)]
    KF[Kafka]
    ML[ML Worker]

    User -->|HTTP| FE
    FE -->|/api, /auth| NG
    NG -->|Reverse Proxy| KS
    KS -->|JDBC| PG
    KS -->|S3 API| MIO
    KS -->|Outbox| KF
    KF -->|Consumer| ML
    ML -->|S3 API| MIO
    ML -->|JDBC| PG
```

## Architecture

The application follows a modular structure with clear separation between pages, shared components, API layer, and state management.

```mermaid
graph TD
    subgraph Entry
        Main[main.jsx]
        App[App.jsx - Router]
    end

    subgraph Pages
        Login[Login]
        Register[Register]
        Dashboard[Dashboard]
        TaskCreate[TaskCreate]
        TaskDetail[TaskDetail]
    end

    subgraph Components
        Layout[Layout]
        ProtectedRoute[ProtectedRoute]
        StatusBadge[StatusBadge]
        Pagination[Pagination]
    end

    subgraph State
        AuthCtx[AuthContext]
        LS[(localStorage - JWT)]
    end

    subgraph API Layer
        Axios[axios.js - interceptors]
        AuthAPI[auth.js]
        TasksAPI[tasks.js]
    end

    subgraph Utils
        Validation[validation.js]
        Multipart[multipart.js]
    end

    Main --> App
    App --> Layout
    Layout --> ProtectedRoute
    ProtectedRoute --> Dashboard
    ProtectedRoute --> TaskCreate
    ProtectedRoute --> TaskDetail
    App --> Login
    App --> Register

    Login --> AuthCtx
    Register --> AuthCtx
    AuthCtx --> AuthAPI
    AuthCtx --> LS

    Dashboard --> TasksAPI
    Dashboard --> StatusBadge
    Dashboard --> Pagination
    TaskCreate --> TasksAPI
    TaskCreate --> Validation
    TaskDetail --> TasksAPI
    TaskDetail --> Multipart
    TaskDetail --> StatusBadge

    AuthAPI --> Axios
    TasksAPI --> Axios
    Axios --> LS
```

### Directory Structure

```
frontend/
├── src/
│   ├── api/                    # Backend API integration
│   │   ├── axios.js            # Axios instance with JWT interceptors
│   │   ├── auth.js             # Auth endpoints (login, register)
│   │   └── tasks.js            # Task CRUD & download endpoints
│   ├── components/             # Reusable UI components
│   │   ├── Layout.jsx          # App shell (header, nav, logout)
│   │   ├── ProtectedRoute.jsx  # Auth guard → redirects to /login
│   │   ├── StatusBadge.jsx     # Task status visual indicator
│   │   ├── Pagination.jsx      # Page navigation controls
│   │   └── *.module.css        # Component-scoped styles
│   ├── context/                # React Context providers
│   │   └── AuthContext.jsx     # Auth state, JWT decode, login/logout
│   ├── pages/                  # Route-level page components
│   │   ├── Login.jsx           # Email/password login form
│   │   ├── Register.jsx        # New account registration form
│   │   ├── Dashboard.jsx       # Task list with filters & pagination
│   │   ├── TaskCreate.jsx      # Image upload + prompt form
│   │   ├── TaskDetail.jsx      # Task info with auto-polling & download
│   │   └── *.module.css        # Page-scoped styles
│   ├── utils/                  # Utility functions
│   │   ├── validation.js       # File type & size validation
│   │   └── multipart.js        # Multipart response parsing
│   ├── styles/
│   │   └── global.css          # CSS variables & base styles
│   ├── main.jsx                # React DOM entry point
│   └── App.jsx                 # Route definitions
├── public/
│   └── index.html              # HTML template
├── package.json                # Dependencies & scripts
├── vite.config.js              # Vite build config + dev proxy
├── Dockerfile                  # Multi-stage Docker build
└── nginx.conf                  # Production reverse proxy config
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Vite over CRA** | Faster HMR, smaller bundles, modern ESM-native tooling |
| **React Context over Redux** | Simple auth state doesn't need external state management |
| **CSS Modules** | Scoped styles without runtime cost; no CSS-in-JS dependency |
| **Axios interceptors** | Centralized JWT injection and 401 handling in one place |
| **Polling over WebSocket** | Simpler to implement; sufficient for current task update frequency |

## Tech Stack

| Category | Technology | Version |
|---|---|---|
| UI Library | React | 18.3.1 |
| Routing | React Router DOM | 6.23.1 |
| HTTP Client | Axios | 1.7.2 |
| Build Tool | Vite | 5.3.1 |
| Language | JavaScript (JSX) | ES2020+ |
| Styling | CSS Modules | — |
| Production Server | Nginx | Alpine |
| Containerization | Docker (multi-stage) | Node 18 + Nginx |

## Setup & Installation

### Prerequisites

- Node.js 18+
- npm 9+

### Run Locally (Development Mode)

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. The dev server proxies `/api` and `/auth` requests to `http://localhost:8080` (Kotlin service).

### Run with Backend

Start the Kotlin service first (see `kotlin-service/README.md`), then:

```bash
cd frontend
npm run dev
```

### Build for Production

```bash
cd frontend
npm run build    # outputs to dist/
npm run preview  # preview production build locally
```

### Run via Docker

```bash
cd frontend
docker build -t modelforge-frontend .
docker run -p 80:80 modelforge-frontend
```

### Full Stack

```bash
cd deploy
docker-compose -f docker-compose.yml \
  -f docker-compose.infra.yml \
  -f docker-compose.app.yml \
  -f docker-compose.frontend.yml \
  up -d --build
```

## Pages & Routing

```mermaid
graph TD
    Root["/ (root)"]
    Login["/login"]
    Register["/register"]
    Dashboard["/dashboard"]
    NewTask["/tasks/new"]
    Detail["/tasks/:id"]
    Any["* (catch-all)"]

    Root -->|redirect| Dashboard
    Any -->|redirect| Dashboard

    subgraph Public Routes
        Login
        Register
    end

    subgraph Protected Routes
        Dashboard
        NewTask
        Detail
    end

    Login -->|on success| Dashboard
    Register -->|on success| Dashboard
    Dashboard -->|"Create task"| NewTask
    Dashboard -->|"Click task"| Detail
    NewTask -->|on success| Detail
    Detail -->|"Back"| Dashboard
```

| Route | Page | Auth | Description |
|---|---|---|---|
| `/login` | Login | Public | Email/password login form |
| `/register` | Register | Public | New account creation |
| `/dashboard` | Dashboard | Protected | Task list with status filter and pagination |
| `/tasks/new` | TaskCreate | Protected | Image upload with drag-drop and optional prompt |
| `/tasks/:id` | TaskDetail | Protected | Task details, auto-polling, 3D model download |
| `*` | — | — | Redirects to `/dashboard` |

## State Management

```mermaid
graph TD
    subgraph AuthContext
        Token[JWT Token]
        UserInfo[User Email]
        IsAuth[isAuthenticated]
    end

    subgraph Actions
        LoginAct[login - email, password]
        RegisterAct[register - email, password]
        LogoutAct[logout]
    end

    subgraph Storage
        LS[(localStorage)]
    end

    LoginAct -->|POST /auth/login| Token
    RegisterAct -->|POST /auth/register| Token
    Token -->|decode JWT| UserInfo
    Token -->|token exists| IsAuth
    Token -->|persist| LS
    LS -->|hydrate on mount| Token
    LogoutAct -->|clear| LS
    LogoutAct -->|reset| Token
```

**Authentication state** is managed via React Context (`AuthContext`):

- On login/register, the JWT token is stored in `localStorage` and decoded to extract the user email
- `isAuthenticated` is derived from the token's presence
- On app mount, the context hydrates from `localStorage` (persists across page reloads)
- `logout()` clears localStorage and resets state

**Component state** uses React hooks (`useState`, `useEffect`) for local concerns:

- Dashboard: tasks list, current page, total pages, status filter, loading/error
- TaskCreate: selected file, image preview, prompt text, upload progress
- TaskDetail: task object, polling interval (3s until terminal state)

## API Integration

```mermaid
sequenceDiagram
    participant Page as React Page
    participant API as API Module
    participant Axios as Axios Instance
    participant LS as localStorage
    participant Backend as Kotlin Service

    Page->>API: fetchTasks() / createTask()
    API->>Axios: HTTP request
    Axios->>LS: Read JWT token
    LS-->>Axios: Bearer token
    Axios->>Backend: Request + Authorization header

    alt 200 OK
        Backend-->>Axios: Response data
        Axios-->>API: Response
        API-->>Page: Data
    else 401 Unauthorized
        Backend-->>Axios: 401 error
        Axios->>LS: Clear token
        Axios->>Page: Redirect to /login
    end
```

### Axios Interceptors

- **Request interceptor** — Reads JWT from `localStorage`, attaches `Authorization: Bearer <token>` header to every request
- **Response interceptor** — On `401` response, clears the stored token and redirects to `/login`

### API Modules

**`auth.js`**
- `login(email, password)` — `POST /auth/login`
- `register(email, password)` — `POST /auth/register`

**`tasks.js`**
- `getTasks(page, size, status)` — `GET /api/tasks` with query params
- `getTask(id)` — `GET /api/tasks/:id`
- `createTask(file, prompt, onProgress)` — `POST /api/tasks` multipart/form-data
- `downloadTask(id)` — `GET /api/tasks/:id/download`

## Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant Login as Login Page
    participant Ctx as AuthContext
    participant API as auth.js
    participant LS as localStorage
    participant Backend as Kotlin Service

    User->>Login: Enter email + password
    Login->>Ctx: login(email, password)
    Ctx->>API: POST /auth/login
    API->>Backend: {email, password}

    alt Valid credentials
        Backend-->>API: {accessToken, tokenType, expiresIn}
        API-->>Ctx: token
        Ctx->>LS: Store token
        Ctx->>Ctx: Decode JWT → extract email
        Ctx->>Ctx: Set isAuthenticated = true
        Ctx-->>Login: Success
        Login->>Login: Navigate to /dashboard
    else Invalid credentials
        Backend-->>API: 401 error
        API-->>Ctx: Error
        Ctx-->>Login: Error message
        Login->>Login: Show error to user
    end
```

### Route Protection

```mermaid
graph TD
    Request["User navigates to protected route"]
    Check{isAuthenticated?}
    Allow["Render page"]
    Deny["Redirect to /login"]

    Request --> Check
    Check -->|Yes| Allow
    Check -->|No| Deny
```

`ProtectedRoute` wraps all authenticated pages. It checks `isAuthenticated` from `AuthContext` and redirects unauthenticated users to `/login`.

## Task Lifecycle

### Task Creation

```mermaid
sequenceDiagram
    actor User
    participant Form as TaskCreate Page
    participant Val as validation.js
    participant API as tasks.js
    participant Backend as Kotlin Service

    User->>Form: Select image file (drag-drop or browse)
    Form->>Val: validateFile(file)

    alt Invalid file
        Val-->>Form: Error (wrong type or > 10MB)
        Form->>Form: Show validation error
    else Valid file
        Val-->>Form: OK
        Form->>Form: Show image preview
    end

    User->>Form: (Optional) Enter text prompt
    User->>Form: Click "Create Task"
    Form->>API: createTask(file, prompt, onProgress)

    loop Upload progress
        API-->>Form: progress percentage
        Form->>Form: Update progress bar
    end

    API->>Backend: POST /api/tasks (multipart)
    Backend-->>API: TaskResponse {id, status: PENDING}
    API-->>Form: task
    Form->>Form: Navigate to /tasks/:id
```

### Task Monitoring & Download

```mermaid
sequenceDiagram
    actor User
    participant Detail as TaskDetail Page
    participant API as tasks.js
    participant Parse as multipart.js
    participant Backend as Kotlin Service

    User->>Detail: Navigate to /tasks/:id
    Detail->>API: getTask(id)
    API->>Backend: GET /api/tasks/:id
    Backend-->>API: Task {status: PROCESSING}
    API-->>Detail: task

    loop Every 3 seconds (while PENDING/PROCESSING)
        Detail->>API: getTask(id)
        API->>Backend: GET /api/tasks/:id
        Backend-->>API: Task {status}
        API-->>Detail: updated task
    end

    Note over Detail: Polling stops on COMPLETED or FAILED

    alt Task COMPLETED
        User->>Detail: Click "Download"
        Detail->>API: downloadTask(id)
        API->>Backend: GET /api/tasks/:id/download
        Backend-->>API: Multipart response (metadata + file)
        API->>Parse: parseMultipart(response)
        Parse-->>API: {metadata, blob}
        API-->>Detail: File blob
        Detail->>Detail: Trigger browser download
    else Task FAILED
        Detail->>Detail: Show error message
    end
```

### Task Status State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: Task created
    PENDING --> PROCESSING: ML worker picks up
    PROCESSING --> COMPLETED: Inference success
    PROCESSING --> FAILED: Inference error
    COMPLETED --> [*]: Download available
    FAILED --> [*]: Error displayed
```

## Deployment

### Docker Build (Multi-stage)

```mermaid
graph LR
    subgraph "Stage 1: Build"
        Node[Node 18]
        Install[npm ci]
        Build[npm run build]
        Dist[dist/]
    end

    subgraph "Stage 2: Serve"
        Nginx[Nginx Alpine]
        Static[Static files]
        Conf[nginx.conf]
    end

    Node --> Install --> Build --> Dist
    Dist -->|COPY| Static
    Conf --> Nginx
    Static --> Nginx
```

### Nginx Routing

```mermaid
graph TD
    Request["Incoming request"]
    API{"/api/* or /auth/*?"}
    SPA["Serve index.html - SPA routing"]
    Proxy["Proxy to kotlin-service:8080"]
    Static{"Static file exists?"}
    File["Serve static file"]

    Request --> API
    API -->|Yes| Proxy
    API -->|No| Static
    Static -->|Yes| File
    Static -->|No| SPA
```

### Nginx Configuration

| Setting | Value |
|---|---|
| SPA routing | `try_files $uri $uri/ /index.html` |
| API proxy | `/api/` and `/auth/` → `http://kotlin-service:8080` |
| Max upload size | 15 MB |
| Health check | `/health` endpoint |

### Docker Compose Configuration

| Setting | Value |
|---|---|
| Port | `80` (configurable via `FRONTEND_PORT`) |
| Memory limit | 128 MB |
| CPU limit | 0.25 cores |
| Depends on | `kotlin-service` |

### File Validation Rules

| Rule | Value |
|---|---|
| Allowed formats | JPG, JPEG, PNG, WebP |
| Max file size | 10 MB |
| Upload method | Multipart form-data |
| Progress tracking | Axios `onUploadProgress` |

## Future Improvements

- **WebSocket notifications** — Replace polling with real-time push updates for task status
- **3D model viewer** — In-browser preview of generated GLB models using Three.js
- **Dark mode** — Theme toggle with CSS variable switching
- **Internationalization (i18n)** — Multi-language support (Russian / English)
- **Offline support** — Service worker for caching static assets and pending uploads
- **E2E tests** — Playwright or Cypress for end-to-end testing
- **Error boundaries** — React error boundaries for graceful failure handling
- **Skeleton loading** — Improve perceived performance with skeleton screens
