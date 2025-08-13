# database.py
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# Cargar la URL de la base de datos desde el archivo .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/srtm_transactions.db")

# Asegurarse de que el directorio de datos exista
db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir)

# Configuración de SQLAlchemy
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelo de la Tabla de Transacciones ---
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    # Se añade la columna timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    msg_type = Column(String, index=True)
    imei = Column(String, index=True)
    request_payload = Column(Text) 
    success = Column(Boolean)
    http_status = Column(Integer)
    response_message = Column(String)
    error_code = Column(String, nullable=True)
    raw_response = Column(Text, nullable=True)
    response_time_ms = Column(Integer)


def create_db_and_tables():
    """Crea la base de datos y las tablas si no existen."""
    try:
        Base.metadata.create_all(bind=engine)
        print("INFO:     Base de datos y tablas verificadas/creadas exitosamente.")
    except Exception as e:
        print(f"ERROR:    No se pudo crear la base de datos. Error: {e}")


def log_transaction(db_session, msg_type: str, request_data: dict, response_data: dict, timestamp: datetime):
    """Guarda un registro de una transacción en la base de datos."""
    try:
        imei = request_data.get("imei", "N/A")

        transaction_record = Transaction(
            # Se guarda el nuevo campo timestamp
            timestamp=timestamp,
            msg_type=msg_type,
            imei=imei,
            request_payload=json.dumps(request_data),
            success=response_data.get('success'),
            http_status=response_data.get('http_status'),
            response_message=response_data.get('message'),
            error_code=response_data.get('error_code'),
            raw_response=response_data.get('raw_response'),
            response_time_ms=int(response_data.get('response_time_ms', 0))
        )
        db_session.add(transaction_record)
        db_session.commit()
        db_session.refresh(transaction_record)
        return transaction_record
    except Exception as e:
        print(f"ERROR:    Fallo al guardar la transacción en la BD: {e}")
        db_session.rollback()
        return None
