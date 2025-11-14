# 🧩 Product Importer – Backend Engineer Assignment

A production-ready FastAPI application built for importing up to **500,000 products** with real-time progress tracking, async background processing, full CRUD UI, and webhook automation.  
Built as part of a backend engineering evaluation for **Acme Inc. / Fulfil.io**.

---

## 🚀 Live Deployment

All services are deployed publicly on a **Google Cloud VM**.

### **Frontend + API**
🔗 http://34.29.230.87

### **API Health Check**
🔗 http://34.29.230.87/api/health  
→ `{ "status": "healthy" }`

The backend uses **Gunicorn, Celery, Redis, PostgreSQL**, managed with **systemd**, ensuring all services automatically restart on VM reboot.

---

## ✔ Assignment Story Coverage

### **STORY 1 — Large CSV Upload (500k rows)**

- Upload via UI (React)
- Streams file in **1MB chunks** (prevents memory spikes)
- Case-insensitive **SKU uniqueness**
- Duplicate SKUs are overwritten (**UPSERT** logic)
- Products default to **active**
- Upload does **not block UI**

---

### **STORY 1A — Real-Time Progress**

Real-time updates via **Server-Sent Events (SSE)**:

- uploading → parsing → importing → completed  
- Live percentage  
- Processed count out of total  
- Full error summary for failed imports  
- Retry option  

---

### **STORY 2 — Product Management UI**

Built using **React CDN + Tailwind + SweetAlert2**:

- Pagination  
- Search: SKU, name, description  
- Filter: Active / Inactive  
- Create / Update / Delete modals  
- SKU uniqueness enforced  

---

### **STORY 3 — Bulk Delete**

- One-click **Delete All Products**
- Confirmation dialog
- Success / failure toast notifications

---

### **STORY 4 — Webhook Management**

- Add / Edit / Delete webhooks  
- Enable / Disable toggle  
- Event types:
  - `product.imported`
  - `product.created`
  - `product.updated`
  - `product.deleted`
- **Test Webhook** button  
- Async dispatch using **Celery**

---

## 🏗 Architecture Overview

```
Frontend (React + Tailwind)
        |
FastAPI Backend (CRUD + CSV + SSE)
        |
Celery Worker (CSV import, webhooks)
        |
Redis (Broker)
        |
PostgreSQL (DB)
```

---

## 📦 Project Structure

```
product-importer/
│── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── tasks.py
│   │   ├── models.py
│   │   └── database.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── ...
│── frontend/
│   └── index.html
│── README.md
│── TESTING.md
│── test_products.csv
```

---

## 🐳 Local Development

### Install dependencies
```bash
pip install -r requirements.txt
```

### Start FastAPI
```bash
uvicorn app.main:app --reload
```

### Start Celery
```bash
celery -A app.tasks worker --loglevel=info
```

---

## 🧪 Testing

```bash
pytest -v --cov=app
```

---

## 📈 Performance Notes

- Handles **500,000-row CSV** using streaming parser  
- Constant memory usage  
- Parallelized import via Celery  
- Immediate UI feedback via SSE  
- All operations optimized for production workloads  

---

## 📝 Additional Notes

- All services (**Gunicorn, Celery, NGINX**) are configured for **automatic restart**
- Fully functional UI without any JS bundler (simple, clean, fast)
- Clean commit history representing thought process and execution
