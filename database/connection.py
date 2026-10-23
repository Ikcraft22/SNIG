from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from config.settings import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

# Crear base para los modelos
Base = declarative_base()

# Motor de base de datos
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def configurar_conexion_sqlite(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

# SessionLocal para obtener sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """
    Generador para obtener sesión de BD.
    Uso en contextos de aplicación web.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Crea todas las tablas en la base de datos."""
    try:
        if (
            engine.dialect.name == "sqlite"
            and engine.url.database not in (None, "", ":memory:")
            and engine.url.query.get("mode") != "memory"
        ):
            with engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA journal_mode=WAL")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        raise

def init_db():
    """Inicializa la base de datos."""
    create_tables()
    logger.info("✅ Base de datos inicializada")
