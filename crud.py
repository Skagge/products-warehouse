from decimal import Decimal

from sqlalchemy.orm import Session
from models import Product, Order, order_product_table, OrderStatus


# Retrieve products from the database
def get_products(db: Session, skip: int = 0, limit: int = 1000):
    return db.query(Product).offset(skip).limit(limit).all()


def create_product(db: Session, name: str, price: Decimal, image_url: str):
    db_product = Product(name=name, price=price, image_url=image_url)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# Delete a product by its ID
def delete_product(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()


def create_order(db: Session, products: list):
    order = Order()  # Create a new order
    db.add(order)  # Add the order to the session
    db.commit()  # Commit the session to generate the `order.id`
    db.refresh(order)  # Refresh the order object to retrieve the generated ID

    for product_id, quantity in products:
        # Fetch the product from the database
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            # Create the order-product association with quantity
            db.execute(
                order_product_table.insert().values(
                    order_id=order.id, product_id=product.id, quantity=quantity
                )
            )
        else:
            raise ValueError(f"Product with ID {product_id} not found.")  # Handle case where product is not found

    db.commit()  # Commit the transaction
    db.refresh(order)  # Refresh the order to get the generated ID and other fields
    return order


def get_in_progress_orders(db: Session):
    # Query orders with the 'IN_PROGRESS' status
    orders = db.query(Order).filter(Order.status.in_(['READY', 'IN_PROGRESS'])).all()

    # Iterate through each order and load the associated products with quantities
    for order in orders:
        total_price = 0  # Initialize total price for the order
        order.products_with_quantity = []

        # Fetch the products and their quantities for the order
        for item in db.query(order_product_table).filter(order_product_table.c.order_id == order.id).all():
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product_price = float(product.price)
            quantity = item.quantity
            total_price += product_price * quantity  # Add the price of the product * quantity to the total
            order.products_with_quantity.append({
                'product': product,
                'quantity': quantity
            })

        order.total_price = total_price  # Store the total price for the order

    return orders

def get_ready_orders(db: Session):
    # Query orders with the 'READY' status
    orders = db.query(Order).filter(Order.status.in_(['READY', 'IN_PROGRESS'])).all()

    # Iterate through each order and load the associated products with quantities
    for order in orders:
        total_price = 0  # Initialize total price for the order
        order.products_with_quantity = []

        # Fetch the products and their quantities for the order
        for item in db.query(order_product_table).filter(order_product_table.c.order_id == order.id).all():
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product_price = float(product.price)
            quantity = item.quantity
            total_price += product_price * quantity  # Add the price of the product * quantity to the total
            order.products_with_quantity.append({
                'product': product,
                'quantity': quantity
            })

        order.total_price = total_price  # Store the total price for the order

    return orders

def get_done_orders(db: Session):
    orders = db.query(Order).filter(Order.status == 'DONE').all()

    total_orders_price = 0

    for order in orders:
        total_price = 0
        order.products_with_quantity = []

        for item in db.query(order_product_table).filter(order_product_table.c.order_id == order.id).all():
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product_price = float(product.price)
            quantity = item.quantity
            total_price += product_price * quantity
            order.products_with_quantity.append({
                'product': product,
                'quantity': quantity
            })

        order.total_price = total_price
        total_orders_price += total_price

    return {"orders": orders, "total_orders_price": total_orders_price}
