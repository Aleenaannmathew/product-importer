# 📦 Product Importer – Backend Engineer Assignment

A high-performance FastAPI application built for importing up to **500,000 products** with real-time progress updates, webhook automation, and complete CRUD management — powered by **Celery, Redis, PostgreSQL, and React**.

Live Deployment: *(Public VM + HTTPS enabled)*  
Tech Stack: FastAPI, SQLAlchemy, Celery, Redis, PostgreSQL, Nginx, React, Tailwind, Docker

---

# 🚀 Objective
This project was built for **Acme Inc.** as part of the Backend Engineer evaluation.  
The goal is to deliver a scalable, production-ready platform for:

- Large CSV imports (up to 500k rows)
- Real-time progress streaming
- Case-insensitive SKU upsert logic
- Product CRUD UI (React)
- Bulk delete operations
- Webhook configuration & dispatching
- Horizontal scalability via Celery workers

---

# 🧩 Feature Breakdown (Mapped to Assignment Stories)

## ✅ STORY 1 — File Upload via UI
- Upload CSV file up to **500,000** records  
- File streamed in **1MB chunks** to avoid memory overload  
- Case-insensitive SKU uniqueness  
- Upsert behavior: duplicate SKUs overwrite existing ones  
- Upload happens asynchronously through Celery  
- Optimized for very large datasets  

---

## ✅ STORY 1A — Real-Time Upload Progress (SSE)
- Server-Sent Events for real-time progress  
- Progress states streamed to UI:

  - `uploading`  
  - `parsing`  
  - `importing`  
  - `completed`  
  - `completed_with_errors`  
  - `failed`  

- UI progress bar + status indicators  
- Detailed error boxes for failed imports  
- One-click retry option  

---

## ✅ STORY 2 — Product Management UI
A complete CRUD dashboard including:

- Pagination  
- Search (SKU, name, description)  
- Filters (Active, Inactive, All)  
- Inline modals for editing / creating  
- Status toggle  
- Delete with confirmation  

---

## ✅ STORY 3 — Bulk Delete
- One-click delete-all  
- Confirmation modal  
- Backend optimized delete for 100k+ rows  
- Success/error notifications  

---

## ✅ STORY 4 — Webhook Management Panel
Supports:

- Add webhook  
- Edit webhook  
- Enable/Disable  
- Delete  
- Test webhook (POST request via Celery)  

Event Types:

- `product.imported`
- `product.created`
- `product.updated`
- `product.deleted`

Webhook calls are **asynchronous**, powered by Celery.

---

# 🏗️ System Architecture

```
          ┌────────────────────────┐
          │     Frontend (React)   │
          │  CSV Upload / CRUD UI  │
          └───────────────┬────────┘
                          │
                          ▼
           ┌────────────────────────┐
           │ FastAPI Backend        │
           │ - File Upload API      │
           │ - Product CRUD API     │
           │ - Webhook API          │
           │ - SSE Progress Stream  │
           └───────────────┬────────┘
                           │ Celery Task Queue
                           ▼
           ┌────────────────────────┐
           │ Celery Worker          │
           │ - Parse CSV in chunks  │
           │ - Upsert Products      │
           │ - Dispatch Webhooks    │
           └───────────────┬────────┘
                           │
                           ▼
           ┌────────────────────────┐
           │ PostgreSQL (Cloud)     │
           └────────────────────────┘

Broker: Redis (Upstash / Local)
Reverse Proxy: Nginx
Deployment: GCP VM
```

---

# 🛠️ Tech Stack

### **Backend**
- FastAPI  
- SQLAlchemy ORM  
- PostgreSQL  
- Redis (as Celery broker)  
- Celery (async processing)  
- Uvicorn + Gunicorn  
- Nginx reverse proxy  

### **Frontend**
- React (CDN build)  
- TailwindCSS  
- SweetAlert2  

### **Infrastructure**
- Docker  
- GCP Compute Engine  
- Supervisor (process manager)  
- HTTPS via Certbot  

---

# 📂 Project Structure

```
product-importer/
│── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── tasks.py
│   │   ├── models.py
│   │   ├── database.py
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
│
│── frontend/
│   └── index.html
│
│── README.md
└── docker-compose.yml (optional)
```

---

# ⚙️ Local Installation

### 1️⃣ Clone Repository
```sh
git clone https://github.com/yourusername/product-importer.git
cd product-importer/backend
```

### 2️⃣ Create Virtual Environment
```sh
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies
```sh
pip install -r requirements.txt
```

### 4️⃣ Run FastAPI Server
```sh
uvicorn app.main:app --reload
```
Access UI:  
👉 http://localhost:8000

---

# 🐳 Docker Setup (Recommended)

```sh
docker-compose up --build
```

This starts:

- FastAPI backend  
- Redis  
- Celery worker  
- PostgreSQL  

---

# 🧪 Tests

Install:
```sh
pip install -r requirements-test.txt
```

Run:
```sh
pytest -v --cov=app
```

---

# 🌐 Deployment Architecture (GCP)

- Nginx → FastAPI (Gunicorn + Uvicorn)
- Supervisor keeps:
  - gunicorn alive
  - celery worker alive
- Certbot auto-renews HTTPS

Server is fully self-healing:
- Restarts after crash
- Restarts after VM reboot
- Celery auto reconnects to Redis

---

# ✔️ Deliverables
- Fully working backend  
- Fully working frontend  
- Deployment link  
- GitHub repository  
- AI tools used  
