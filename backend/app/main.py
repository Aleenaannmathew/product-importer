from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel, constr
import asyncio
import json
import uuid
import os
from datetime import datetime

from .database import get_db, engine, Base
from .models import Product, Webhook, ImportJob
from .tasks import process_csv_import


app = FastAPI(title="Product Importer API", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(BaseModel):
    sku: constr(strip_whitespace=True, min_length=1, max_length=100)
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    description: Optional[str] = ""
    active: Optional[bool] = True

class ProductUpdate(BaseModel):
    sku: Optional[constr(strip_whitespace=True, min_length=1, max_length=100)] = None
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class WebhookCreate(BaseModel):
    url: str
    event_type: str = "product.imported"
    enabled: Optional[bool] = True

class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    event_type: Optional[str] = None
    enabled: Optional[bool] = None


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}



@app.post("/api/products/import")
async def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload CSV file for import"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files are allowed")
    
   
    job_id = str(uuid.uuid4())
    job = ImportJob(id=job_id, status="pending")
    db.add(job)
    db.commit()
    
   
    upload_dir = "temp_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{job_id}.csv")
    
    
    file_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024): 
            f.write(chunk)
            file_size += len(chunk)
    
    file_size_mb = file_size / (1024 * 1024)
    
    
    
    
    
    from .tasks import process_csv_import_sync
    import threading
    thread = threading.Thread(target=process_csv_import_sync, args=(job_id, file_path))
    thread.daemon = True
    thread.start()
   
    
    return {"job_id": job_id, "status": "processing", "file_size_mb": round(file_size_mb, 2)}

@app.get("/api/products/import/{job_id}/progress")
async def import_progress(job_id: str, db: Session = Depends(get_db)):
    """SSE endpoint for real-time progress WITH ERROR DETAILS"""
    async def event_generator():
        try:
            if not job_id or len(job_id) != 36:
                yield f"data: {json.dumps({'status': 'invalid_id'})}\n\n"
                return
        except Exception:
            yield f"data: {json.dumps({'status': 'invalid_id'})}\n\n"
            return
        
        for _ in range(600): 
            db.expire_all()
            job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
            
            if not job:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break
            
            total = job.total_rows if job.total_rows > 0 else 1
            percent = int((job.processed_rows / total * 100)) if total > 0 else 0
            
            progress = {
                "status": job.status,
                "processed": job.processed_rows,
                "total": job.total_rows,
                "percent": percent,
                "error": job.error_message 
            }
            
            yield f"data: {json.dumps(progress)}\n\n"
            
            if job.status in ["completed", "completed_with_errors", "failed"]:
                break
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/products")
def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    active: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get paginated products with filters"""
    query = db.query(Product)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.sku.ilike(search_term)) |
            (Product.name.ilike(search_term)) |
            (Product.description.ilike(search_term))
        )
    
    if active and active != "all":
        query = query.filter(Product.active == (active == "true"))
    
    total = query.count()
    products = query.order_by(Product.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "products": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "active": p.active,
                "created_at": p.created_at.isoformat() if p.created_at else None
            } for p in products
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
    }

@app.post("/api/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create new product manually"""
    sku_lower = product.sku.strip().lower()
    
   
    existing = db.query(Product).filter(func.lower(Product.sku) == sku_lower).first()
    if existing:
        raise HTTPException(400, f"Product with SKU '{product.sku}' already exists")
    
    new_product = Product(
        sku=product.sku.strip(),
        name=product.name.strip(),
        description=product.description.strip() if product.description else "",
        active=product.active
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
   
    
    return {
        "id": new_product.id,
        "sku": new_product.sku,
        "name": new_product.name,
        "status": "success"
    }

@app.get("/api/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get single product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "active": product.active,
        "created_at": product.created_at.isoformat() if product.created_at else None
    }

@app.put("/api/products/{product_id}")
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    
    if product_update.sku and product_update.sku.strip().lower() != product.sku.lower():
        sku_lower = product_update.sku.strip().lower()
        existing = db.query(Product).filter(
            func.lower(Product.sku) == sku_lower,
            Product.id != product_id
        ).first()
        if existing:
            raise HTTPException(400, f"Product with SKU '{product_update.sku}' already exists")
    
   
    if product_update.sku is not None:
        product.sku = product_update.sku.strip()
    if product_update.name is not None:
        product.name = product_update.name.strip()
    if product_update.description is not None:
        product.description = product_update.description.strip()
    if product_update.active is not None:
        product.active = product_update.active
    
    product.updated_at = datetime.utcnow()
    db.commit()
    
    
    return {"status": "success", "id": product.id}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete single product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    sku = product.sku
    db.delete(product)
    db.commit()
    

    
    return {"status": "success"}

@app.post("/api/products/bulk-delete")
def bulk_delete_products(db: Session = Depends(get_db)):
    """Delete all products"""
    count = db.query(Product).count()
    db.query(Product).delete()
    db.commit()
    
   
    
    return {"status": "success", "message": f"Deleted {count} products", "count": count}



@app.get("/api/webhooks")
def get_webhooks(db: Session = Depends(get_db)):
    """Get all webhooks"""
    webhooks = db.query(Webhook).all()
    return {
        "webhooks": [
            {
                "id": w.id,
                "url": w.url,
                "event_type": w.event_type,
                "enabled": w.enabled,
                "created_at": w.created_at.isoformat() if w.created_at else None
            } for w in webhooks
        ]
    }

@app.get("/api/webhooks/{webhook_id}")
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Get single webhook by ID"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    return {
        "id": webhook.id,
        "url": webhook.url,
        "event_type": webhook.event_type,
        "enabled": webhook.enabled,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None
    }

@app.post("/api/webhooks")
def create_webhook(webhook: WebhookCreate, db: Session = Depends(get_db)):
    """Create new webhook"""
    new_webhook = Webhook(
        url=webhook.url,
        event_type=webhook.event_type,
        enabled=webhook.enabled
    )
    db.add(new_webhook)
    db.commit()
    db.refresh(new_webhook)
    
  
    
    return {"id": new_webhook.id, "status": "success"}

@app.put("/api/webhooks/{webhook_id}")
def update_webhook(
    webhook_id: int,
    webhook_update: WebhookUpdate,
    db: Session = Depends(get_db)
):
    """Update webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    if webhook_update.url is not None:
        webhook.url = webhook_update.url
    if webhook_update.event_type is not None:
        webhook.event_type = webhook_update.event_type
    if webhook_update.enabled is not None:
        webhook.enabled = webhook_update.enabled
    
    db.commit()
    

    
    return {"status": "success", "id": webhook.id}

@app.delete("/api/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Delete webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    url = webhook.url
    db.delete(webhook)
    db.commit()
    
  
    
    return {"status": "success"}

@app.post("/api/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Test webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                webhook.url,
                json={"event": "test", "timestamp": datetime.utcnow().isoformat()},
                timeout=10.0
            )
            return {"status_code": response.status_code, "status": "success"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)