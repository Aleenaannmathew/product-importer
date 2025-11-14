# 📦 Product Importer – Backend Engineer Assignment  
A high-performance FastAPI application designed for importing **up to 500,000 products** from CSV, with **real-time progress tracking**, full **CRUD UI**, **webhook support**, and **asynchronous background processing** using Celery + Redis.

Deployment: **Render (Free Tier)**  
Tech Stack: `FastAPI`, `SQLAlchemy`, `Celery`, `Redis`, `PostgreSQL`, `React`, `Docker`

---

## 🚀 **Objective**

This project was built for **Acme Inc.** as part of a backend engineering evaluation.  
The core goal is to implement a production-ready web application capable of:

- Importing large CSV files (up to **500,000 rows**)
- Real-time progress updates (SSE)
- Case-insensitive SKU upsert logic
- Complete CRUD UI for products
- Bulk delete operations
- Webhook configuration + event triggers
- Horizontally scalable async processing

---

# 🧩 **Features Mapped to Assignment Stories**

## ✅ **STORY 1 — File Upload via UI**

✔ Upload CSV up to **500,000 records**  
✔ Files streamed to disk in **1 MB chunks** (prevents memory overload)  
✔ Case-insensitive SKU uniqueness  
✔ Upsert: duplicate SKUs are automatically **overwritten**  
✔ Products created as **active** by default  
✔ Large files do not block UI

---

## ✅ **STORY 1A — Upload Progress Visibility**

✔ Real-time progress via **Server-Sent Events (SSE)**  
✔ Progress states sent to UI:
- `uploading`
- `parsing`
- `importing`
- `completed`
- `completed_with_errors`
- `failed`

✔ Detailed error summary when import fails  
✔ Automatic retry option from UI  
✔ Frontend progress bar with % and record counters

---

## ✅ **STORY 2 — Product Management UI**

✔ Full CRUD UI using **React + Tailwind**  
✔ Features:

- Pagination  
- Search by SKU/name/description  
- Filter by Active/Inactive/All  
- Inline edit modals (SweetAlert2)  
- SKU uniqueness enforced  
- User-friendly design  

---

## ✅ **STORY 3 — Bulk Delete**

✔ Single-click “Delete All Products”  
✔ Confirmation modal  
✔ Toast notifications on success/failure  

---

## ✅ **STORY 4 — Webhook Management**

✔ Add/Edit/Delete webhooks  
✔ Enable/Disable switch  
✔ Support for event types:
- `product.imported`
- `product.created`
- `product.updated`
- `product.deleted`

✔ Test webhook button (sends POST request)  
✔ Celery-powered async webhook dispatching  

---

# 🏗️ **System Architecture**

mathematica
Copy code
              ┌────────────────────────┐
              │       Frontend (React)  │
              │  Upload CSV / CRUD / UI │
              └───────────────┬────────┘
                              │
                              ▼
               ┌────────────────────────┐
               │ FastAPI Backend        │
               │ - File Upload API      │
               │ - Product CRUD API     │
               │ - Webhook API          │
               │ - SSE Progress API     │
               └───────────────┬────────┘
                               │ enqueue job
                               ▼
               ┌────────────────────────┐
               │ Celery Worker          │
               │ - Chunked CSV parsing  │
               │ - Upsert products      │
               │ - Send webhooks        │
               └───────────────┬────────┘
                               │
                               ▼
               ┌────────────────────────┐
               │ PostgreSQL (Render)    │
               └────────────────────────┘
markdown
Copy code

Broker: **Upstash Redis Free Tier**  
Deployment: **Render Web Service + Worker**

---

# 🛠️ **Tech Stack**

### **Backend**
- FastAPI  
- SQLAlchemy ORM  
- PostgreSQL  
- Celery  
- Redis (Upstash)  
- Uvicorn + Gunicorn  

### **Frontend**
- React ( CDN )  
- TailwindCSS  
- SweetAlert2  

### **Infra**
- Docker  
- Render (Free Tier)  
- Upstash Redis (Free tier)  

### **Testing**
- pytest  
- pytest-cov  

---

# 📂 **Project Structure**

product-importer/
│── backend/
│ ├── app/
│ │ ├── main.py
│ │ ├── tasks.py
│ │ ├── models.py
│ │ ├── database.py
│ │ └── ...
│ ├── tests/
│ ├── Dockerfile
│ ├── requirements.txt
│ └── docker-compose.yml
│
│── frontend/
│ └── index.html (React UI)
│
│── README.md
│── .gitignore



# ⚙️ **Installation (Local Setup)**

## 1️⃣ Clone Repository

git clone https://github.com/yourusername/product-importer.git
cd product-importer/backend


2️⃣ Create Virtual Environment

python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux
3️⃣ Install Dependencies

pip install -r requirements.txt

4️⃣ Run FastAPI Server

uvicorn app.main:app --reload
Visit:
👉 http://localhost:8000

🐳 Docker Setup (Recommended)
Build & run all services:

docker-compose up --build

This starts:

FastAPI backend

Celery worker

Redis

PostgreSQL

🧪 Running Tests

Install test dependencies:
pip install -r requirements-test.txt

Run all tests:
pytest -v --cov=app