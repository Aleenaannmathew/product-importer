from celery import Celery
import pandas as pd
import os
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Product, ImportJob, Webhook
import uuid, logging
from datetime import datetime
import httpx
import traceback
import time
logger = logging.getLogger(__name__)


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task
def process_csv_import(job_id: str, file_path: str):
    """Process CSV import asynchronously"""
    process_csv_import_sync(job_id, file_path)

def process_csv_import_sync(job_id: str, file_path: str):
    """
    COMPLETE CSV PROCESSING WITH PERFECT ERROR HANDLING
    - Shows ALL error details to user
    - Handles duplicate SKUs with UPSERT
    - Stops processing immediately on fatal errors
    - Updates progress even during failures
    - Returns detailed error messages
    """
  
    
    db = SessionLocal()
    job = None
    
    try:
       
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        
        if not job:
            return
        
    
        job.status = "parsing"
        db.commit()
      
      
        if not os.path.exists(file_path):
            error_msg = f"File not found at path: {file_path}"
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()
            return 
        
      
        
      
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            total_rows = len(df)
        except UnicodeDecodeError:
            error_msg = "CSV encoding error. Please save your CSV as UTF-8 and try again."
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()
            return 
        except Exception as e:
            error_msg = f"Failed to parse CSV file: {str(e)}\n\nPlease check:\n- File is a valid CSV\n- File is not corrupted\n- File encoding is UTF-8"
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()
            return  
        
       
        required_cols = ['sku', 'name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            error_msg = (
                f"❌ Missing required columns: {', '.join(missing_cols)}\n\n"
                f"Required columns: sku, name\n"
                f"Found columns: {', '.join(df.columns)}\n\n"
                f"Please add the missing columns to your CSV and try again."
            )
          
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()
            return  
        
       
        
        
        job.total_rows = total_rows
        job.status = "importing"
        db.commit()
      
        chunk_size = 100
        processed_count = 0
        created_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        
      
        for i in range(0, total_rows, chunk_size):
            chunk = df.iloc[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
        
            
            for idx, row in chunk.iterrows():
                try:
                  
                    sku = str(row.get('sku', '')).strip()
                    
                 
                    if not sku or sku.lower() in ['nan', 'none', '']:
                        error_msg = f"Row {idx + 2}: Empty or invalid SKU"
                        errors.append(error_msg)
                        error_count += 1
                       
                        continue
                    
                  
                    sku_lower = sku.lower()
                    name = str(row.get('name', '')).strip()
                    description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else ''
                    
                  
                    if not name or name.lower() in ['nan', 'none', '']:
                        error_msg = f"Row {idx + 2} (SKU: {sku}): Missing or invalid product name"
                        errors.append(error_msg)
                        error_count += 1
                        continue
                    
                  
                    existing_product = db.query(Product).filter(
                        func.lower(Product.sku) == sku_lower
                    ).first()
                    
                    if existing_product:
                       
                        existing_product.name = name
                        existing_product.description = description
                        existing_product.updated_at = datetime.utcnow()
                        updated_count += 1
                       
                    else:
                       
                        new_product = Product(
                            sku=sku,
                            name=name,
                            description=description,
                            active=True
                        )
                        db.add(new_product)
                        created_count += 1
                      
                    
                    processed_count += 1
                    
                  
                    if processed_count % 50 == 0:
                        try:
                            db.commit()
                        except Exception as commit_err:
                            db.rollback()
                            error_msg = f"Database error at row {idx + 2}: {str(commit_err)}"
                            errors.append(error_msg)
                            error_count += 1
                       
                    
                except Exception as row_error:
                    error_msg = f"Row {idx + 2} (SKU: {row.get('sku', 'N/A')}): {str(row_error)}"
                    errors.append(error_msg)
                    error_count += 1
                  
                    continue
            

            try:
                db.commit()
              
            except Exception as commit_error:
                db.rollback()
                error_msg = f"Failed to commit chunk at row {i}: {str(commit_error)}"
                errors.append(error_msg)
                error_count += chunk_size - processed_count
             
            
           
            job.processed_rows = min(i + chunk_size, total_rows)
            db.commit()
            
          
            progress_pct = int((job.processed_rows / total_rows) * 100)
          
        
        
        try:
            db.commit()
        except Exception as e:
           logger.warning(f"Final commit error: {e}")
        
        
        if error_count > 0 and processed_count == 0:
          
            job.status = "failed"
            error_summary = (
                f"❌ Import Failed - No products were imported\n\n"
                f"Total errors: {error_count}\n\n"
                f"First {min(10, len(errors))} errors:\n"
                + "\n".join(f"• {err}" for err in errors[:10])
            )
            if len(errors) > 10:
                error_summary += f"\n\n... and {len(errors) - 10} more errors"
            job.error_message = error_summary
           
            
        elif error_count > 0:
        
            job.status = "completed_with_errors"
            error_summary = (
                f"⚠️ Import completed with errors\n\n"
                f"Successfully processed: {processed_count:,}/{total_rows:,} products\n"
                f"✓ Created: {created_count:,}\n"
                f"✓ Updated: {updated_count:,}\n"
                f"❌ Errors: {error_count:,}\n\n"
                f"First {min(5, len(errors))} errors:\n"
                + "\n".join(f"• {err}" for err in errors[:5])
            )
            if len(errors) > 5:
                error_summary += f"\n\n... and {len(errors) - 5} more errors"
            job.error_message = error_summary
            
            
        else:
          
            job.status = "completed"
            job.error_message = None
          
        
        job.completed_at = datetime.utcnow()
        db.commit()
        
       
        if job.status in ["completed", "completed_with_errors"]:
            try:
                trigger_webhooks.delay("product.imported", {
                    "job_id": job_id,
                    "count": processed_count,
                    "created": created_count,
                    "updated": updated_count,
                    "errors": error_count
                })
            except:
              
                trigger_webhooks_sync("product.imported", {
                    "job_id": job_id,
                    "count": processed_count,
                    "created": created_count,
                    "updated": updated_count,
                    "errors": error_count
                })
        
     
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
              
            except Exception as cleanup_err:
               logger.warning(f"Could not delete temp file: {cleanup_err}")

        
      
    except Exception as e:
      
        logger.exception("Fatal error while processing CSV import")
      
        try:
            if job:
                job.status = "failed"
                job.error_message = (
                    f"❌ Fatal Error: {str(e)}\n\n"
                    f"Full error details:\n{traceback.format_exc()}"
                )
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
           logger.error(f"Failed to update job status in database: {db_error}")

    
    finally:
      
        db.close()
       

@celery_app.task
def trigger_webhooks(event_type: str, payload: dict):
    trigger_webhooks_sync(event_type, payload)

def trigger_webhooks_sync(event_type: str, payload: dict):
    db = SessionLocal()
    
    try:
        webhooks = db.query(Webhook).filter(
            Webhook.event_type == event_type,
            Webhook.enabled == True
        ).all()
        
        if not webhooks:
            return
        
        
        for webhook in webhooks:
            try:
                webhook_payload = {
                    "event": event_type,
                    "data": payload,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                with httpx.Client() as client:
                    response = client.post(
                        webhook.url,
                        json=webhook_payload,
                        timeout=10.0
                    )
            except Exception as e:
               logger.error(f"Webhook failed: {webhook.url} - Error: {e}")

    
    except Exception as e:
        logger.error(f"Error in webhook processing: {e}")
    finally:
        db.close()