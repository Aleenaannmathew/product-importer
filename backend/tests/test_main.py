"""
Complete test suite for Product Importer API
Tests all CRUD operations, CSV upload, webhooks, and edge cases
"""

import pytest
import os
import io
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from faker import Faker

from app.main import app
from app.database import Base, get_db
from app.models import Product, Webhook, ImportJob


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

fake = Faker()


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create test database before each test and clean up after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_product():
    """Create a sample product for testing"""
    db = TestingSessionLocal()
    product = Product(
        sku="TEST-001",
        name="Test Product",
        description="Test Description",
        active=True
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db.close()
    return product

@pytest.fixture
def sample_webhook():
    """Create a sample webhook for testing"""
    db = TestingSessionLocal()
    webhook = Webhook(
        url="https://webhook.site/test",
        event_type="product.imported",
        enabled=True
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    db.close()
    return webhook

@pytest.fixture
def sample_csv():
    """Generate a sample CSV file"""
    csv_content = """sku,name,description
PROD-001,Product 1,Description 1
PROD-002,Product 2,Description 2
PROD-003,Product 3,Description 3
"""
    return io.BytesIO(csv_content.encode())



def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"




class TestProductCRUD:
    """Test all product CRUD operations"""
    
    def test_create_product_success(self):
        """Test creating a new product"""
        product_data = {
            "sku": "NEW-001",
            "name": "New Product",
            "description": "New Description",
            "active": True
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "NEW-001"
        assert data["status"] == "success"
    
    def test_create_product_duplicate_sku(self, sample_product):
        """Test creating product with duplicate SKU fails"""
        product_data = {
            "sku": "TEST-001",
            "name": "Duplicate Product",
            "description": "Should fail"
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_product_case_insensitive_sku(self, sample_product):
        """Test SKU uniqueness is case-insensitive"""
        product_data = {
            "sku": "test-001", 
            "name": "Should Fail",
            "description": "Case insensitive"
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 400
    
    def test_get_products_list(self, sample_product):
        """Test getting paginated product list"""
        response = client.get("/api/products?page=1&per_page=20")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["products"]) >= 1
    
    def test_get_products_with_search(self, sample_product):
        """Test product search functionality"""
        response = client.get("/api/products?search=TEST")
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) >= 1
        assert "TEST" in data["products"][0]["sku"]
    
    def test_get_products_with_active_filter(self, sample_product):
        """Test filtering by active status"""
        response = client.get("/api/products?active=true")
        assert response.status_code == 200
        data = response.json()
        for product in data["products"]:
            assert product["active"] == True
    
    def test_get_single_product(self, sample_product):
        """Test getting a single product by ID"""
        response = client.get(f"/api/products/{sample_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_product.id
        assert data["sku"] == sample_product.sku
    
    def test_get_nonexistent_product(self):
        """Test getting a product that doesn't exist"""
        response = client.get("/api/products/99999")
        assert response.status_code == 404
    
    def test_update_product(self, sample_product):
        """Test updating a product"""
        update_data = {
            "name": "Updated Name",
            "description": "Updated Description",
            "active": False
        }
        response = client.put(f"/api/products/{sample_product.id}", json=update_data)
        assert response.status_code == 200
        
       
        response = client.get(f"/api/products/{sample_product.id}")
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Description"
        assert data["active"] == False
    
    def test_update_product_sku(self, sample_product):
        """Test updating product SKU"""
        update_data = {"sku": "TEST-002"}
        response = client.put(f"/api/products/{sample_product.id}", json=update_data)
        assert response.status_code == 200
        
       
        response = client.get(f"/api/products/{sample_product.id}")
        assert response.json()["sku"] == "TEST-002"
    
    def test_update_product_duplicate_sku(self):
        """Test updating to duplicate SKU fails"""
    
        db = TestingSessionLocal()
        p1 = Product(sku="PROD-A", name="Product A", active=True)
        p2 = Product(sku="PROD-B", name="Product B", active=True)
        db.add_all([p1, p2])
        db.commit()
        
      
        update_data = {"sku": "PROD-A"}
        response = client.put(f"/api/products/{p2.id}", json=update_data)
        assert response.status_code == 400
        db.close()
    
    def test_delete_product(self, sample_product):
        """Test deleting a product"""
        response = client.delete(f"/api/products/{sample_product.id}")
        assert response.status_code == 200
        
      
        response = client.get(f"/api/products/{sample_product.id}")
        assert response.status_code == 404
    
    def test_bulk_delete(self, sample_product):
        """Test bulk delete all products"""
    
        db = TestingSessionLocal()
        for i in range(5):
            product = Product(sku=f"BULK-{i}", name=f"Product {i}", active=True)
            db.add(product)
        db.commit()
        db.close()
        
        response = client.post("/api/products/bulk-delete")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] >= 5
        
        response = client.get("/api/products")
        assert response.json()["total"] == 0



class TestCSVUpload:
    """Test CSV upload and import functionality"""
    
    def test_upload_csv_success(self, sample_csv):
        """Test successful CSV upload"""
        files = {"file": ("test.csv", sample_csv, "text/csv")}
        response = client.post("/api/products/import", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
    
    def test_upload_non_csv_file(self):
        """Test uploading non-CSV file fails"""
        txt_content = io.BytesIO(b"Not a CSV")
        files = {"file": ("test.txt", txt_content, "text/plain")}
        response = client.post("/api/products/import", files=files)
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]
    
    def test_csv_with_duplicate_skus(self):
        """Test CSV with duplicate SKUs (should overwrite)"""
        csv_content = """sku,name,description
DUP-001,First,Description 1
DUP-001,Second,Description 2
"""
        csv_file = io.BytesIO(csv_content.encode())
        files = {"file": ("test.csv", csv_file, "text/csv")}
        response = client.post("/api/products/import", files=files)
        assert response.status_code == 200
    
    def test_csv_missing_required_columns(self):
        """Test CSV with missing required columns"""
        csv_content = """sku,description
PROD-001,No name column
"""
        csv_file = io.BytesIO(csv_content.encode())
        files = {"file": ("test.csv", csv_file, "text/csv")}
        response = client.post("/api/products/import", files=files)
      
        assert response.status_code == 200
    
    def test_import_progress_endpoint(self, sample_csv):
        """Test import progress tracking"""
       
        files = {"file": ("test.csv", sample_csv, "text/csv")}
        response = client.post("/api/products/import", files=files)
        job_id = response.json()["job_id"]
        
        response = client.get(f"/api/products/import/{job_id}/progress")
        assert response.status_code == 200
    
    def test_import_progress_invalid_job_id(self):
        """Test progress with invalid job ID"""
        response = client.get("/api/products/import/invalid-id/progress")
        assert response.status_code == 200   


class TestWebhooks:
    """Test webhook CRUD operations"""
    
    def test_create_webhook(self):
        """Test creating a webhook"""
        webhook_data = {
            "url": "https://webhook.site/test-123",
            "event_type": "product.imported",
            "enabled": True
        }
        response = client.post("/api/webhooks", json=webhook_data)
        assert response.status_code == 200
        assert "id" in response.json()
    
    def test_get_webhooks_list(self, sample_webhook):
        """Test getting all webhooks"""
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert "webhooks" in data
        assert len(data["webhooks"]) >= 1
    
    def test_get_single_webhook(self, sample_webhook):
        """Test getting a single webhook"""
        response = client.get(f"/api/webhooks/{sample_webhook.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_webhook.id
        assert data["url"] == sample_webhook.url
    
    def test_update_webhook(self, sample_webhook):
        """Test updating a webhook"""
        update_data = {
            "url": "https://webhook.site/updated",
            "enabled": False
        }
        response = client.put(f"/api/webhooks/{sample_webhook.id}", json=update_data)
        assert response.status_code == 200
        
       
        response = client.get(f"/api/webhooks/{sample_webhook.id}")
        data = response.json()
        assert data["url"] == "https://webhook.site/updated"
        assert data["enabled"] == False
    
    def test_delete_webhook(self, sample_webhook):
        """Test deleting a webhook"""
        response = client.delete(f"/api/webhooks/{sample_webhook.id}")
        assert response.status_code == 200
        
   
        response = client.get(f"/api/webhooks/{sample_webhook.id}")
        assert response.status_code == 404
    
    def test_test_webhook(self, sample_webhook):
        """Test webhook testing functionality"""
        response = client.post(f"/api/webhooks/{sample_webhook.id}/test")
        assert response.status_code == 200
      


class TestEdgeCases:
    """Test edge cases and validation"""
    
    def test_empty_sku(self):
        """Test creating product with empty SKU"""
        product_data = {
            "sku": "",
            "name": "No SKU",
            "description": "Should fail"
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 422 
    
    def test_empty_name(self):
        """Test creating product with empty name"""
        product_data = {
            "sku": "TEST-EMPTY",
            "name": "",
            "description": "Empty name"
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 422 
    
    def test_very_long_sku(self):
        """Test product with very long SKU"""
        product_data = {
            "sku": "A" * 200, 
            "name": "Long SKU Product",
            "description": "Testing limits"
        }
        response = client.post("/api/products", json=product_data)
       
        assert response.status_code in [200, 400, 422]
    
    def test_special_characters_in_sku(self):
        """Test SKU with special characters"""
        product_data = {
            "sku": "TEST-@#$%",
            "name": "Special Chars",
            "description": "Special characters in SKU"
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 200 
    
    def test_unicode_in_product_name(self):
        """Test product with unicode characters"""
        product_data = {
            "sku": "UNICODE-001",
            "name": "Product 产品 🎉",
            "description": "Unicode characters"
        }
        response = client.post("/api/products", json=product_data)
        assert response.status_code == 200
    
    def test_pagination_edge_cases(self):
        """Test pagination with edge cases"""
      
        response = client.get("/api/products?page=0")
        assert response.status_code == 422  
        
      
        response = client.get("/api/products?page=9999")
        assert response.status_code == 200
        
       
        response = client.get("/api/products?per_page=1000")
        assert response.status_code == 422 
    
    def test_invalid_webhook_url(self):
        """Test creating webhook with invalid URL"""
        webhook_data = {
            "url": "not-a-valid-url",
            "event_type": "product.imported"
        }
        response = client.post("/api/webhooks", json=webhook_data)
       
        assert response.status_code == 200


class TestPerformance:
    """Test performance with larger datasets"""
    
    def test_create_many_products(self):
        """Test creating multiple products"""
        db = TestingSessionLocal()
        products = []
        for i in range(100):
            product = Product(
                sku=f"PERF-{i:04d}",
                name=f"Performance Test Product {i}",
                description=f"Test description {i}",
                active=True
            )
            products.append(product)
        
        db.bulk_save_objects(products)
        db.commit()
        db.close()
        
        response = client.get("/api/products")
        assert response.json()["total"] == 100
    
    def test_search_performance(self):
        """Test search with many products"""
        db = TestingSessionLocal()
        for i in range(50):
            product = Product(
                sku=f"SEARCH-{i:04d}",
                name=f"Searchable Product {i}",
                active=True
            )
            db.add(product)
        db.commit()
        db.close()
    
        response = client.get("/api/products?search=SEARCH")
        assert response.status_code == 200
        assert len(response.json()["products"]) <= 20 



class TestIntegration:
    """Test complete workflows"""
    
    def test_complete_product_lifecycle(self):
        """Test full product lifecycle: create -> read -> update -> delete"""
        create_data = {
            "sku": "LIFECYCLE-001",
            "name": "Lifecycle Product",
            "description": "Testing complete lifecycle"
        }
        response = client.post("/api/products", json=create_data)
        assert response.status_code == 200
        product_id = response.json()["id"]
        
       
        response = client.get(f"/api/products/{product_id}")
        assert response.status_code == 200
        assert response.json()["sku"] == "LIFECYCLE-001"
        
      
        update_data = {"name": "Updated Lifecycle Product"}
        response = client.put(f"/api/products/{product_id}", json=update_data)
        assert response.status_code == 200
        
       
        response = client.get(f"/api/products/{product_id}")
        assert response.json()["name"] == "Updated Lifecycle Product"
        
  
        response = client.delete(f"/api/products/{product_id}")
        assert response.status_code == 200
        
      
        response = client.get(f"/api/products/{product_id}")
        assert response.status_code == 404
    
    def test_csv_import_to_product_list(self):
        """Test CSV import workflow"""
       
        csv_content = """sku,name,description
IMPORT-001,Imported Product 1,Description 1
IMPORT-002,Imported Product 2,Description 2
"""
        csv_file = io.BytesIO(csv_content.encode())
        files = {"file": ("test.csv", csv_file, "text/csv")}
        response = client.post("/api/products/import", files=files)
        assert response.status_code == 200
        
       
        import time
        time.sleep(2)
        

        response = client.get("/api/products?search=IMPORT")
     
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app", "--cov-report=html"])