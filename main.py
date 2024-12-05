# Standard Library Imports
import os
from decimal import Decimal
from io import BytesIO
from typing import List

# Third-Party Imports
from fastapi import FastAPI, Form, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from PIL import Image

# Local Imports
from models import SessionLocal, Product, Order, order_product_table
import crud
from fastapi.templating import Jinja2Templates


app = FastAPI()

templates = Jinja2Templates(directory="templates")

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/cashier-routing", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("cashier-routing.html", {"request": request})

@app.get("/products", response_class=HTMLResponse)
def cashier_page(request: Request, db: Session = Depends(get_db)):
    products = crud.get_products(db)
    return templates.TemplateResponse("products.html", {"request": request, "products": products})

@app.get("/create-order", response_class=HTMLResponse)
def create_order(request: Request, db: Session = Depends(get_db)):
    products = crud.get_products(db)
    return templates.TemplateResponse("create-order.html", {"request": request, "products": products})

@app.get("/current-orders")
async def get_current_orders(request: Request, db: Session = Depends(get_db)):
    in_progress_orders = crud.get_in_progress_orders(db)
    return templates.TemplateResponse("current-orders.html", {"request": request, "orders": in_progress_orders})

@app.get("/dispenser", response_class=HTMLResponse)
async def get_ready_orders(request: Request, db: Session = Depends(get_db)):
    ready_orders = crud.get_ready_orders(db)
    return templates.TemplateResponse("dispenser.html", {"request": request, "orders": ready_orders})

@app.get("/earnings", response_class=HTMLResponse)
async def get_ready_orders(request: Request, db: Session = Depends(get_db)):
    done_orders = crud.get_done_orders(db)
    return templates.TemplateResponse("earnings.html", {"request": request, "orders": done_orders})

class ProductOrder(BaseModel):
    product_id: int
    quantity: int

class CreateOrderRequest(BaseModel):
    products: List[ProductOrder]

@app.post("/create-order")
def create_order_route(order_request: CreateOrderRequest, db: Session = Depends(get_db)):
    try:
        products = [(product.product_id, product.quantity) for product in order_request.products]

        order = crud.create_order(db, products)
        return {"message": "Order created successfully", "order_id": order.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.patch("/update-order-status/{order_id}")
async def update_order_status(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    status_transitions = {
        "IN_PROGRESS": "READY",
        "READY": "DONE",
    }

    next_status = status_transitions.get(order.status.value)
    if not next_status:
        raise HTTPException(status_code=400, detail=f"Order cannot transition from {order.status}")

    order.status = next_status
    db.commit()
    db.refresh(order)

    return {"message": f"Zamówienie poszło dalej!"}

@app.post("/add-product")
async def add_product(
    name: str = Form(...),
    price: Decimal = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validate the inputs
    if not name:
        raise HTTPException(status_code=400, detail="Product name is required.")
    if price < 0:
        raise HTTPException(status_code=400, detail="Price must be a positive value.")
    if price != price.quantize(Decimal("0.01")):
        raise HTTPException(status_code=400, detail="Price must have at most two decimal places.")

    # Save the image to the uploads directory
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist

    # Generate a unique file name for the uploaded image
    file_extension = os.path.splitext(image.filename)[-1].lower()
    if file_extension not in [".jpg", ".jpeg", ".png", ".gif"]:
        raise HTTPException(status_code=400, detail="Invalid image format. Accepted formats are .jpg, .jpeg, .png, .gif")

    unique_filename = f"{name.replace(' ', '_')}_{image.filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Open the image using Pillow
    image_content = await image.read()
    img = Image.open(BytesIO(image_content))

    # Resize the image to 200x200 pixels (you can adjust the size as needed)
    img = img.resize((200, 200))

    # Save the resized image
    img.save(file_path)

    # Create the product in the database with the image URL
    image_url = f"/{file_path}"  # Relative path to the saved image
    crud.create_product(db, name=name, price=price, image_url=image_url)

    return RedirectResponse(url="/products", status_code=303)


@app.delete("/delete-product/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    # Fetch the product by ID
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Produkt nie został znaleziony")

    # Check if there are any orders associated with this product
    orders_with_product = db.query(Order).join(order_product_table).filter(
        order_product_table.c.product_id == product_id).all()

    if orders_with_product:
        raise HTTPException(status_code=400,
                            detail="Produkt nie może zostać usunięty, ponieważ jest powiązany z zamówieniem")

    # Proceed to delete the product if no orders are associated
    db.delete(product)
    db.commit()

    return {"message": "Produkt został usunięty"}

from fastapi import HTTPException

@app.delete("/delete-all-orders")
async def delete_all_orders(db: Session = Depends(get_db)):
    try:
        # Delete all records from the order_product_table
        db.execute(order_product_table.delete())
        # Delete all records from the orders table
        db.query(Order).delete()
        db.commit()
        return {"message": "All orders and related products have been deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while deleting data.")