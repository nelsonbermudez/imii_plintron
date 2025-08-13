# models.py
from datetime import datetime
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field, model_validator
import re

# --- Modelos de Solicitud de Acciones (SIN CAMBIOS) ---
# ... (todos los modelos de Registro, Cancelacion, etc. permanecen aquí sin cambios)
class RegistroPositivoRequest(BaseModel):
    """Modelo para la solicitud de registro positivo (1001)."""
    imei: Optional[str] = Field(None, description="El IMEI del dispositivo a registrar.", example="852055059447491")
    tipo_usuario_propietario: Optional[str] = Field(None, description="Tipo de usuario propietario. 1: Natural, 2: Jurídico.", example="1")
    tipo_identificacion_propietario: Optional[str] = Field(None, description="Tipo de identificación. 1: Cédula, 4: CE, etc.", example="1")
    identificacion_propietario: Optional[str] = Field(None, description="Número de identificación del propietario.", example="22222222222")
    nombre_razon_social_propietario: Optional[str] = Field(None, description="Nombre completo o razón social del propietario.", example="Fulano de Tal")
    direccion_propietario: Optional[str] = Field(None, description="Dirección del propietario.", example="kra 1 # 23-45 Bogota Bogota")
    telefono_contacto_propietario: Optional[str] = Field(None, description="Teléfono de contacto del propietario.", example="3580666666")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales.", example="Solicitud de registro inicial de cliente.")
    imsi: Optional[str] = Field(None, description="IMSI del dispositivo (opcional).", example="732101000000001")
    msisdn: Optional[str] = Field(None, description="Número de línea (opcional).", example="3588777777")

    @model_validator(mode='before')
    @classmethod
    def check_required_fields(cls, data: Any) -> Any:
        """Valida que todos los campos requeridos estén presentes."""
        if not isinstance(data, dict):
            return data
        
        required_fields = [
            'imei', 'tipo_usuario_propietario', 'tipo_identificacion_propietario', 
            'identificacion_propietario', 'nombre_razon_social_propietario', 
            'direccion_propietario', 'telefono_contacto_propietario', 'observaciones'
        ]
        for field in required_fields:
            if data.get(field) is None:
                raise ValueError(f"El campo '{field}' es obligatorio.")
        return data

class RegistroNegativoRequest(BaseModel):
    """Modelo para la solicitud de registro negativo por robo/pérdida (2001)."""
    imei: Optional[str] = Field(None, description="El IMEI del dispositivo a reportar.", example="852055059447491")
    tipo_reporte: Optional[str] = Field(None, description="Causa del reporte. '1': Robo, '2': Extravío, etc.", example="1")
    nombre_reporte: Optional[str] = Field(None, description="Nombre de quien reporta.", example="Fulano de Tal")
    tipo_identificacion_reporte: Optional[str] = Field(None, description="Tipo de identificación de quien reporta.", example="1")
    identificacion_reporte: Optional[str] = Field(None, description="Número de identificación de quien reporta.", example="22222222222")
    telefono_reporte: Optional[str] = Field(None, description="Teléfono de contacto de quien reporta.", example="3585555555")
    direccion_reporte: Optional[str] = Field(None, description="Dirección de quien reporta.", example="Calle 123 #45-67")
    ciudad_reporte: Optional[str] = Field(None, description="Ciudad donde ocurrió el incidente.", example="Bogota")
    departamento_reporte: Optional[str] = Field(None, description="Departamento donde ocurrió el incidente.", example="BOGOTA")
    correo_electronico: Optional[str] = Field(None, description="Email de contacto.", example="nelsonberm@gmail.com")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales.", example="Reporte de robo con violencia.")
    empleo_violencia: Optional[str] = Field(None, description="¿Se usó violencia? '0': No, '1': Si. Obligatorio si tipo_reporte es '1'.", example="1")
    utilizacion_armas: Optional[str] = Field(None, description="¿Se usaron armas? '0': Fuego, '1': Blanca, '2': Otras. Obligatorio si tipo_reporte es '1' y empleo_violencia es '1'.", example="1")
    victima_menor_edad: Optional[str] = Field(None, description="¿La víctima fue menor de edad? '0': No, '1': Si. Obligatorio si tipo_reporte es '1' y empleo_violencia es '1'.", example="0")

    @model_validator(mode='before')
    @classmethod
    def check_required_and_robo_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        always_required = [
            'imei', 'tipo_reporte', 'nombre_reporte', 'tipo_identificacion_reporte', 'identificacion_reporte',
            'telefono_reporte', 'direccion_reporte', 'ciudad_reporte', 'departamento_reporte', 'correo_electronico', 'observaciones'
        ]
        for field in always_required:
            if data.get(field) is None:
                raise ValueError(f"El campo '{field}' es obligatorio.")

        if data.get('tipo_reporte') == '1':
            if data.get('empleo_violencia') is None:
                raise ValueError("El campo 'empleo_violencia' es obligatorio cuando 'tipo_reporte' es '1' (Robo).")
            
            if data.get('empleo_violencia') == '1':
                if data.get('utilizacion_armas') is None:
                    raise ValueError("El campo 'utilizacion_armas' es obligatorio cuando 'empleo_violencia' es '1'.")
                if data.get('victima_menor_edad') is None:
                    raise ValueError("El campo 'victima_menor_edad' es obligatorio cuando 'empleo_violencia' es '1'.")
        
        return data

class CancelacionNegativoRequest(BaseModel):
    """Modelo para la solicitud de cancelación de un registro negativo (3001)."""
    imei: Optional[str] = Field(None, description="El IMEI del dispositivo a desbloquear.", example="8577055059447491")
    fecha_reporte: Optional[str] = Field(
        None, 
        description="Fecha del reporte original en formato YYYYMMDDHHMMSS.", 
        example="20241025143000"
    )
    observaciones: Optional[str] = Field(None, description="Razón de la cancelación.", example="Cancelacion de reporte por recuperacion del equipo.")

    @model_validator(mode='before')
    @classmethod
    def check_required_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Validar campos obligatorios
            if data.get('imei') is None: 
                raise ValueError("El campo 'imei' es obligatorio.")
            if data.get('fecha_reporte') is None: 
                raise ValueError("El campo 'fecha_reporte' es obligatorio.")
            if data.get('observaciones') is None: 
                raise ValueError("El campo 'observaciones' es obligatorio.")
            
            # Validar formato de fecha_reporte
            fecha_reporte = data.get('fecha_reporte')
            if fecha_reporte:
                # Validar que tenga exactamente 14 dígitos
                if not re.match(r'^\d{14}$', fecha_reporte):
                    raise ValueError("El campo 'fecha_reporte' debe tener el formato YYYYMMDDHHMMSS (14 dígitos).")
                
                # Validar que sea una fecha válida
                try:
                    datetime.strptime(fecha_reporte, '%Y%m%d%H%M%S')
                except ValueError:
                    raise ValueError("El campo 'fecha_reporte' contiene una fecha/hora inválida. Use el formato YYYYMMDDHHMMSS.")
                
        return data

class ModificacionPositivoRequest(BaseModel):
    """Modelo para la solicitud de modificación de un registro positivo (4001)."""
    imei: Optional[str] = Field(None, description="El IMEI del dispositivo a modificar.", example="852055059447491")
    tipo_modificacion: Optional[str] = Field(None, description="Tipo de modificación a realizar. 1: Venta Inicial, 2: Titularidad, 3: Modificación.", example="2")
    tipo_usuario_propietario: Optional[str] = Field(None, description="Tipo de usuario del NUEVO propietario.", example="1")
    tipo_identificacion_propietario: Optional[str] = Field(None, description="Tipo de ID del NUEVO propietario.", example="1")
    identificacion_propietario: Optional[str] = Field(None, description="Número de ID del NUEVO propietario.", example="222222222222")
    nombre_razon_social_propietario: Optional[str] = Field(None, description="Nombre del NUEVO propietario.", example="Fulano de Tal (Nuevo Titular)")
    direccion_propietario: Optional[str] = Field(None, description="Dirección del NUEVO propietario.", example="Calle 123 #45-67")
    telefono_contacto_propietario: Optional[str] = Field(None, description="Teléfono de contacto del NUEVO propietario.", example="3580666666")
    tipo_usuario_autorizado: Optional[str] = Field(None, description="Indica si existe un usuario autorizado. '0': No, '1' o '2': Sí.", example="1")
    imsi: Optional[str] = Field(None, description="IMSI del dispositivo (opcional).", example="732101000000001")
    msisdn: Optional[str] = Field(None, description="Número de línea (opcional).", example="3588777777")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales.", example="Cambio de titularidad por venta.")
    tipo_identificacion_propietario_anterior: Optional[str] = Field(None, description="Tipo de ID del propietario ANTERIOR. Obligatorio si tipo_modificacion es '2' o '3'.", example="1")
    identificacion_propietario_anterior: Optional[str] = Field(None, description="Número de ID del propietario ANTERIOR. Obligatorio si tipo_modificacion es '2' o '3'.", example="12345678")
    tipo_identificacion_autorizado: Optional[str] = Field(None, description="Tipo de identificación del autorizado. Requerido si tipo_usuario_autorizado no es '0'.", example="1")
    identificacion_autorizado: Optional[str] = Field(None, description="Número de identificación del autorizado. Requerido si tipo_usuario_autorizado no es '0'.", example="22222222222")
    nombre_razon_social_autorizado: Optional[str] = Field(None, description="Nombre del autorizado. Requerido si tipo_usuario_autorizado no es '0'.", example="Fulano de Tal (Autorizado)")
    direccion_autorizado: Optional[str] = Field(None, description="Dirección del autorizado. Requerido si tipo_usuario_autorizado no es '0'.", example="Avenida Siempre Viva 742")
    telefono_contacto_autorizado: Optional[str] = Field(None, description="Teléfono de contacto del autorizado. Requerido si tipo_usuario_autorizado no es '0'.", example="3580666666")

    @model_validator(mode='before')
    @classmethod
    def check_all_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        always_required = [
            'imei', 'tipo_modificacion', 'tipo_usuario_propietario', 'tipo_identificacion_propietario',
            'identificacion_propietario', 'nombre_razon_social_propietario', 'direccion_propietario',
            'telefono_contacto_propietario', 'tipo_usuario_autorizado'
        ]
        for field in always_required:
            if data.get(field) is None:
                raise ValueError(f"El campo '{field}' es obligatorio.")

        if data.get('tipo_modificacion') in ['2', '3']:
            if data.get('tipo_identificacion_propietario_anterior') is None:
                raise ValueError("El campo 'tipo_identificacion_propietario_anterior' es obligatorio cuando 'tipo_modificacion' es '2' o '3'.")
            if data.get('identificacion_propietario_anterior') is None:
                raise ValueError("El campo 'identificacion_propietario_anterior' es obligatorio cuando 'tipo_modificacion' es '2' o '3'.")

        if data.get('tipo_usuario_autorizado') != '':
            autorizado_fields = [
                'tipo_identificacion_autorizado', 'identificacion_autorizado', 'nombre_razon_social_autorizado',
                'direccion_autorizado', 'telefono_contacto_autorizado'
            ]
            for field in autorizado_fields:
                if data.get(field) is None:
                    raise ValueError(f"El campo '{field}' es obligatorio cuando 'tipo_usuario_autorizado' no es '0'.")
        
        return data

class CancelacionPositivoRequest(BaseModel):
    """Modelo para la solicitud de cancelación de un registro positivo (5001)."""
    imei: Optional[str] = Field(None, description="IMEI a eliminar de la lista positiva.", example="852055059447491")
    tipo_usuario_propietario: Optional[str] = Field(None, description="Tipo de usuario del propietario.", example="1")
    tipo_identificacion_propietario: Optional[str] = Field(None, description="Tipo de identificación del propietario.", example="1")
    identificacion_propietario: Optional[str] = Field(None, description="Número de identificación del propietario.", example="222222222222")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales.", example="Cancelacion por fin de servicio.")

    @model_validator(mode='before')
    @classmethod
    def check_required_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            required_fields = ['imei', 'tipo_usuario_propietario', 'tipo_identificacion_propietario', 'identificacion_propietario', 'observaciones']
            for field in required_fields:
                if data.get(field) is None:
                    raise ValueError(f"El campo '{field}' es obligatorio.")
        return data
        
# --- Modelos de Consulta ---

class ConsultaNegativaRequest(BaseModel):
    """Modelo para una solicitud de consulta negativa por IMEI."""
    imei: str = Field(..., description="El IMEI del dispositivo a consultar.", example="862055059447491", min_length=15, max_length=15)

class ConsultaPositivaRequest(BaseModel):
    """Modelo para una solicitud de consulta positiva."""
    imei: str = Field(..., description="El IMEI del dispositivo.", min_length=15, max_length=15)
    tipo_identificacion_propietario: str = Field(..., description="Tipo de identificación del propietario. Ej: '1' para Cédula.")
    identificacion_propietario: str = Field(..., description="Número de identificación del propietario.")


# --- Modelo de Respuesta de la API ---

class APIResponse(BaseModel):
    """Modelo unificado para las respuestas de la API."""
    success: bool
    http_status: int
    message: Optional[str] = None
    error_code: Optional[str] = None
    raw_response: Optional[Any] = None
    transaction_timestamp: str = Field(..., description="Fecha y hora de la transacción en formato UTC.")