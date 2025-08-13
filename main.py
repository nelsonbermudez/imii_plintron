# main.py
import uvicorn
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends, Path
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.orm import Session
from dataclasses import asdict

load_dotenv()

from models import (
    RegistroPositivoRequest, RegistroNegativoRequest, CancelacionNegativoRequest,
    ModificacionPositivoRequest, CancelacionPositivoRequest, APIResponse,
    ConsultaNegativaRequest, ConsultaPositivaRequest
)
from soap_client import SRTMAxisClient, SRTMResponse, logger
from consulta_client import ConsultaDBAClient, ConsultaDBAResponse
import database

app = FastAPI(
    title="SRTM Wrapper API v1.5",
    description="API REST para interactuar con los servicios SOAP SRTM de acciones y consultas, con errores de validación descriptivos.",
    version="1.5.0",
)

# ========================================
# CONFIGURACIÓN CORS - MUY IMPORTANTE
# ========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:8080",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8000",  # Para swagger docs
        "http://127.0.0.1:8000",
        # Agregar otros puertos si es necesario
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "accept",
        "accept-encoding", 
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "cache-control"
    ],
    expose_headers=["*"],
    max_age=86400,  # 24 horas
)

@app.on_event("startup")
def on_startup():
    global soap_client, consulta_client
    database.create_db_and_tables()
    
    logger.info("🚀 Iniciando SRTM API...")
    
    try:
        soap_client = SRTMAxisClient(
            endpoint=os.getenv("SRTM_ENDPOINT"),
            user_id=os.getenv("SRTM_USER"),
            password=os.getenv("SRTM_PASSWORD")
        )
        logger.info("✅ Cliente SOAP de acciones inicializado correctamente")
    except Exception as e:
        logger.critical(f"FATAL: No se pudo inicializar el cliente SOAP de acciones. Error: {e}")
        soap_client = None
        
    try:
        consulta_client = ConsultaDBAClient(
            endpoint=os.getenv("CONSULTA_ENDPOINT"),
            user_id=os.getenv("CONSULTA_USER"),
            password=os.getenv("CONSULTA_PASSWORD")
        )
        logger.info("✅ Cliente SOAP de consultas inicializado correctamente")
    except Exception as e:
        logger.critical(f"FATAL: No se pudo inicializar el cliente SOAP de consultas. Error: {e}")
        consulta_client = None
    
    logger.info("🎯 SRTM API lista para recibir requests")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========================================
# HEALTH CHECK ENDPOINT
# ========================================
@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud de la API
    """
    return {
        "status": "ok", 
        "message": "SRTM API funcionando correctamente",
        "version": "1.5.0",
        "cors_enabled": True,
        "services": {
            "soap_client": soap_client is not None,
            "consulta_client": consulta_client is not None
        }
    }

# ========================================
# MANEJO DE ERRORES
# ========================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """
    Manejador de errores de validación mejorado para informar qué campos fallan.
    """
    formatted_errors = []
    for error in exc.errors():
        # error['loc'] es una tupla, ej: ('body', 'nombre_del_campo')
        field_name = str(error['loc'][-1])
        # error['msg'] contiene la razón del error, ej: "Field required"
        message = error['msg']
        
        # Creamos un mensaje de error claro y específico
        formatted_errors.append(f"Campo '{field_name}': {message}")
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Error de validación en la solicitud. Uno o más campos son inválidos o están ausentes.",
            "errors": formatted_errors,
            "success": False,
            "http_status": 422,
            "error_code": "VALIDATION_ERROR"
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Error no controlado en {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        content={
            "detail": f"Ocurrió un error interno en el servidor: {str(exc)}",
            "success": False,
            "http_status": 500,
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )

def create_api_response(soap_response):
    if not soap_response.success and soap_response.http_status >= 500:
        raise HTTPException(status_code=soap_response.http_status, detail=soap_response.message)
    return APIResponse(
        success=soap_response.success,
        http_status=soap_response.http_status,
        message=soap_response.message,
        error_code=soap_response.error_code,
        raw_response=soap_response.raw_response,
        transaction_timestamp=soap_response.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    )

# ========================================
# ENDPOINTS DE ACCIONES SRTM
# ========================================

@app.post("/registro-positivo", response_model=APIResponse, summary="1001: Registrar un IMEI en la lista positiva", tags=["Acciones SRTM"])
async def registro_positivo(request: RegistroPositivoRequest, db: Session = Depends(get_db)):
    if not soap_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de acciones no inicializado.")
    
    logger.info(f"📝 Procesando registro positivo para IMEI: {request.imei}")
    soap_response = soap_client.registrar_positivo(request)
    database.log_transaction(db, 'action', os.getenv("MSG_TYPE_REGISTRO_POSITIVO"), request.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)
    
@app.post("/registro-negativo", response_model=APIResponse, summary="2001: Reportar un IMEI por robo o pérdida", tags=["Acciones SRTM"])
async def registro_negativo(request: RegistroNegativoRequest, db: Session = Depends(get_db)):
    if not soap_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de acciones no inicializado.")
    
    logger.info(f"🚨 Procesando registro negativo para IMEI: {request.imei}")
    soap_response = soap_client.registrar_negativo(request)
    database.log_transaction(db, 'action', os.getenv("MSG_TYPE_REGISTRO_NEGATIVO"), request.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)

@app.post("/cancelacion-negativo", response_model=APIResponse, summary="3001: Cancelar un reporte de robo/pérdida", tags=["Acciones SRTM"])
async def cancelacion_negativo(request: CancelacionNegativoRequest, db: Session = Depends(get_db)):
    """
    Cancela un registro negativo existente en la BDA.
    
    **Campos requeridos:**
    - `imei`: IMEI del dispositivo (15 dígitos)
    - `fecha_reporte`: Fecha del reporte original en formato YYYYMMDDHHMMSS
    - `observaciones`: Razón de la cancelación
    
    **Ejemplo de request:**
    ```json
    {
        "imei": "8577055059447491",
        "fecha_reporte": "20241025143000",
        "observaciones": "Cancelacion de reporte por recuperacion del equipo."
    }
    ```
    """
    if not soap_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de acciones no inicializado.")
    
    logger.info(f"✅ Procesando cancelación negativo para IMEI: {request.imei}, Fecha: {request.fecha_reporte}")
    soap_response = soap_client.cancelar_negativo(request)
    database.log_transaction(db, 'action', os.getenv("MSG_TYPE_CANCELACION_NEGATIVO"), request.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)


@app.post("/modificacion-positivo", response_model=APIResponse, summary="4001: Modificar un registro positivo existente", tags=["Acciones SRTM"])
async def modificacion_positivo(request: ModificacionPositivoRequest, db: Session = Depends(get_db)):
    if not soap_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de acciones no inicializado.")
    
    logger.info(f"🔄 Procesando modificación positivo para IMEI: {request.imei}")
    soap_response = soap_client.modificar_positivo(request)
    database.log_transaction(db, 'action', os.getenv("MSG_TYPE_MODIFICACION_POSITIVO"), request.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)

@app.post("/cancelacion-positivo", response_model=APIResponse, summary="5001: Cancelar un registro de la lista positiva", tags=["Acciones SRTM"])
async def cancelacion_positivo(request: CancelacionPositivoRequest, db: Session = Depends(get_db)):
    if not soap_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de acciones no inicializado.")
    
    logger.info(f"❌ Procesando cancelación positivo para IMEI: {request.imei}")
    soap_response = soap_client.cancelar_positivo(request)
    database.log_transaction(db, 'action', os.getenv("MSG_TYPE_CANCELACION_POSITIVO"), request.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)

# ========================================
# ENDPOINTS DE CONSULTAS BDA
# ========================================
    
@app.post("/consulta/positiva", response_model=APIResponse, summary="Consultar IMEI en BDA Positiva", tags=["Consultas BDA"])
async def consulta_positiva(request: ConsultaPositivaRequest, db: Session = Depends(get_db)):
    if not consulta_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de consultas no inicializado.")
    
    logger.info(f"🔍 Procesando consulta positiva para IMEI: {request.imei}")
    soap_response = consulta_client.consulta_positiva(
        imei=request.imei,
        tipo_id_propietario=request.tipo_identificacion_propietario,
        id_propietario=request.identificacion_propietario
    )
    
    database.log_transaction(db, 'query', 'consultaBDAPositiva', request.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)

@app.get("/consulta/negativa/{imei}", response_model=APIResponse, summary="Consultar IMEI en BDA Negativa", tags=["Consultas BDA"])
async def consulta_negativa(imei: str = Path(..., min_length=15, max_length=15, pattern="^[0-9]*$"), db: Session = Depends(get_db)):
    if not consulta_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de consultas no inicializado.")
    
    logger.info(f"🔍 Procesando consulta negativa para IMEI: {imei}")
    request_model = ConsultaNegativaRequest(imei=imei)
    soap_response = consulta_client.consulta_negativa(imei)
    
    database.log_transaction(db, 'query', 'consultaBDANegativa', request_model.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)
    
@app.get("/consulta/negativa/tipo-reporte/{imei}", response_model=APIResponse, summary="Consultar tipo de reporte de un IMEI en BDA Negativa", tags=["Consultas BDA"])
async def consulta_negativa_tipo_reporte(imei: str = Path(..., min_length=15, max_length=15, pattern="^[0-9]*$"), db: Session = Depends(get_db)):
    if not consulta_client:
        raise HTTPException(status_code=503, detail="Servicio no disponible: Cliente SOAP de consultas no inicializado.")
    
    logger.info(f"🔍 Procesando consulta tipo reporte para IMEI: {imei}")
    request_model = ConsultaNegativaRequest(imei=imei)
    soap_response = consulta_client.consulta_negativa_tipo_reporte(imei)
    
    database.log_transaction(db, 'query', 'consultaBDANegativaTipoReporte', request_model.model_dump(), asdict(soap_response), soap_response.timestamp)
    return create_api_response(soap_response)

# ========================================
# ENDPOINT ADICIONAL DE INFORMACIÓN
# ========================================

@app.get("/info", summary="Información de la API", tags=["Info"])
async def api_info():
    """
    Endpoint que proporciona información general sobre la API
    """
    return {
        "api_name": "SRTM Wrapper API",
        "version": "1.5.0",
        "description": "API REST para interactuar con los servicios SOAP SRTM",
        "cors_enabled": True,
        "endpoints": {
            "acciones": [
                "POST /registro-positivo",
                "POST /registro-negativo", 
                "POST /cancelacion-negativo",
                "POST /modificacion-positivo",
                "POST /cancelacion-positivo"
            ],
            "consultas": [
                "POST /consulta/positiva",
                "GET /consulta/negativa/{imei}",
                "GET /consulta/negativa/tipo-reporte/{imei}"
            ],
            "utilidad": [
                "GET /health",
                "GET /info",
                "GET /docs",
                "GET /redoc"
            ]
        },
        "frontend_origins_allowed": [
            "http://localhost:3000",
            "http://localhost:8080", 
            "http://localhost:5000"
        ]
    }

# ========================================
# INICIO DEL SERVIDOR
# ========================================

if __name__ == "__main__":
    print("🚀 Iniciando servidor SRTM API...")
    print("📋 Configuración:")
    print(f"   - Puerto: 8000")
    print(f"   - Host: 0.0.0.0")
    print(f"   - Docs: http://localhost:8000/docs")
    print(f"   - Health: http://localhost:8000/health")
    print(f"   - CORS habilitado para puertos: 3000, 8080, 5000")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )