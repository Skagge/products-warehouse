from sqlalchemy import create_engine, Column, Integer, String, Numeric, Table, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from enum import Enum as PyEnum

DATABASE_URL = "sqlite:///./test.db"

Base = declarative_base()

class OrderStatus(PyEnum):
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    DONE = "DONE"

order_product_table = Table(
    'order_product',
    Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('quantity', Integer, nullable=False)
)

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String, nullable=True)


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.IN_PROGRESS, nullable=False)
    products = relationship(
        'Product',
        secondary=order_product_table,
        back_populates='orders'
    )

Product.orders = relationship(
    'Order',
    secondary=order_product_table,
    back_populates='products'
)

engine = create_engine(DATABASE_URL)

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)