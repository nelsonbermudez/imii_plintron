# soap_client.py
import logging
import os
import html
import time
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from zeep import Client, Settings, Transport
from zeep.exceptions import Fault
from requests import Session
from lxml import etree
from dotenv import load_dotenv

from models import (
    RegistroPositivoRequest, RegistroNegativoRequest, CancelacionNegativoRequest,
    ModificacionPositivoRequest, CancelacionPositivoRequest
)

# Cargar variables de entorno desde .env
load_dotenv()

# --- Configuración del Logging Centralizado ---
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.hasHandlers():
    file_handler = logging.FileHandler(os.path.join(log_dir, 'srtm_api.log'), mode='a', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# --- Modelo de Respuesta Unificado ---
@dataclass
class SRTMResponse:
    """Dataclass para la respuesta interna del cliente SOAP."""
    success: bool = False
    http_status: int = 500
    response_time_ms: float = 0.0
    message: Optional[str] = "An internal error occurred."
    error_code: Optional[str] = None
    raw_response: Optional[str] = None
    # Se añade el timestamp para pasarlo a las capas superiores
    timestamp: datetime = field(default_factory=datetime.utcnow)

class SRTMAxisClient:
    SERVICE_NAMESPACE = "http://service.client.xcewsmulti.iecisa.es"
    OPERADOR_ID = "00020" 

    def __init__(self, endpoint: str, user_id: str, password: str):
        if not all([endpoint, user_id, password]):
            raise ValueError("Endpoint, User ID, and Password must be provided.")
        self.endpoint = endpoint
        self.user_id = user_id
        self.password = password
        self.message_counter = int(time.time()) % 100000
        self.proc_counter = int(time.time()) % 100000

        try:
            wsdl_path = 'srtm_minimal.wsdl'
            self.client = Client(wsdl=wsdl_path, transport=Transport(session=Session(), timeout=30), settings=Settings(strict=False, xml_huge_tree=True))
            self.client.service._binding_options['address'] = self.endpoint
        except FileNotFoundError:
            logger.critical("Error Crítico: No se encontró 'srtm_minimal.wsdl'.")
            raise
        except Exception as e:
            logger.critical(f"Error Crítico al inicializar el cliente SOAP: {e}")
            raise
        logger.info("🔧 Cliente SRTM Python (Zeep) inicializado correctamente.")

    def _generate_id(self, prefix: str, length: int) -> str:
        timestamp = datetime.now().strftime("%Y%m%d")
        if prefix == "msg":
            self.message_counter += 1
            sequence = f"{self.message_counter:07d}"
            return f"{self.OPERADOR_ID}{timestamp}{sequence}"
        else: 
            self.proc_counter += 1
            sequence = f"{self.proc_counter:05d}"
            return f"{self.OPERADOR_ID}{timestamp}{prefix}{sequence}"

    @staticmethod
    def _get_current_datetime() -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _escape_xml(text: Optional[str]) -> str:
        return html.escape(text, quote=True) if text else ""

    def _build_xml(self, msg_type: str, body_content: str, observaciones: Optional[str]) -> str:
        process_type_map = {
            os.getenv("MSG_TYPE_REGISTRO_POSITIVO"): "01",
            os.getenv("MSG_TYPE_REGISTRO_NEGATIVO"): "02",
            os.getenv("MSG_TYPE_CANCELACION_NEGATIVO"): "03",
            os.getenv("MSG_TYPE_MODIFICACION_POSITIVO"): "04",
            os.getenv("MSG_TYPE_CANCELACION_POSITIVO"): "05",
        }
        process_id = self._generate_id(process_type_map.get(msg_type, "00"), 5)
        message_id = self._generate_id("msg", 7)
        
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<MensajeBDA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
            '\t<CabeceraMensaje>',
            f'\t\t<IdentificadorProceso>{process_id}</IdentificadorProceso>',
            f'\t\t<IdentificadorMensaje>{message_id}</IdentificadorMensaje>',
            f'\t\t<FechaCreacionMsg>{self._get_current_datetime()}</FechaCreacionMsg>',
            f'\t\t<TipoMsg>{msg_type}</TipoMsg>',
            f'\t\t<Emisor>{self.OPERADOR_ID}</Emisor>',
            '\t\t<Destinatario>00000</Destinatario>',
            f'\t\t<Observaciones>{self._escape_xml(observaciones)}</Observaciones>' if observaciones else '',
            '\t</CabeceraMensaje>',
            '\t<CuerpoMensaje>',
            body_content,
            '\t</CuerpoMensaje>',
            '</MensajeBDA>'
        ]
        return '\n'.join(filter(None, xml_parts))

    def _send_request(self, msg_type: str, xml_payload: str) -> SRTMResponse:
        # Se captura el timestamp al inicio del envío
        transaction_time = datetime.utcnow()
        response = SRTMResponse(timestamp=transaction_time)
        start_time = time.time()
        
        logger.info(f"--- INICIO TRANSACCIÓN (TipoMsg: {msg_type}) ---\nRequest XML:\n{xml_payload}")

        try:
            escaped_xml = self._escape_xml(xml_payload)
            soap_envelope = (
                f'<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                f'<ns1:receiveMessage xmlns:ns1="{self.SERVICE_NAMESPACE}">'
                f'<userId>{self.user_id}</userId><password>{self.password}</password><xmlMsg>{escaped_xml}</xmlMsg>'
                f'</ns1:receiveMessage></soap:Body></soap:Envelope>'
            )

            boundary = f'----={uuid.uuid4().hex}'
            start_cid = f'<{uuid.uuid4().hex}>'
            payload = "\r\n".join([
                f'--{boundary}', 'Content-Type: text/xml; charset=utf-8', f'Content-ID: {start_cid}', '', soap_envelope,
                f'--{boundary}', 'Content-Type: text/plain', 'Content-ID: <sender>', '', self.OPERADOR_ID,
                f'--{boundary}', 'Content-Type: text/plain', 'Content-ID: <receiver>', '', '00000',
                f'--{boundary}', 'Content-Type: text/plain', 'Content-ID: <typeMsg>', '', msg_type, f'--{boundary}--'
            ])
            headers = {'Content-Type': f'multipart/related; type="text/xml"; start="{start_cid}"; boundary="{boundary}"', 'SOAPAction': '""'}

            http_res = self.client.transport.session.post(self.endpoint, data=payload.encode('utf-8'), headers=headers, timeout=30)
            
            response.http_status = http_res.status_code
            http_res.raise_for_status()

            res_env = etree.fromstring(http_res.content)
            result_text = res_env.findtext('.//{*}receiveMessageReturn', default='').strip()
            
            response.raw_response = result_text
            if result_text == "ack":
                response.success = True
                response.message = f"Solicitud {msg_type} aceptada."
            else:
                response.success = False
                response.message = f"Solicitud {msg_type} rechazada por el servidor."
                response.error_code = result_text

        except Fault as fault:
            logger.error(f"SOAP Fault (TipoMsg: {msg_type}): {fault.message}", exc_info=True)
            response.message = f"Error SOAP: {fault.message}"
            response.raw_response = str(fault.detail)
        except Exception as e:
            logger.error(f"Error inesperado (TipoMsg: {msg_type}): {e}", exc_info=True)
            response.message = f"Error inesperado en la comunicación: {str(e)}"
        finally:
            response.response_time_ms = (time.time() - start_time) * 1000
            log_message = (
                f"--- FIN TRANSACCIÓN (TipoMsg: {msg_type}) ---\n"
                f"Resultado: {'Éxito' if response.success else 'Fallo'} | Mensaje: {response.message} | "
                f"Respuesta Raw: {response.raw_response} | Duración: {response.response_time_ms:.2f} ms"
            )
            logger.info(log_message)

        return response

    def registrar_positivo(self, req: RegistroPositivoRequest) -> SRTMResponse:
        body = (
            f"<SolicitudRegistroPositivo>"
            f"<Imei>{req.imei}</Imei>" +
            (f"<Imsi>{self._escape_xml(req.imsi)}</Imsi>" if req.imsi else "") +
            (f"<Msisdn>{self._escape_xml(req.msisdn)}</Msisdn>" if req.msisdn else "") +
            (f"<NombreRazonSocialPropietario>{self._escape_xml(req.nombre_razon_social_propietario)}</NombreRazonSocialPropietario>" if req.nombre_razon_social_propietario else "") +
            (f"<DireccionPropietario>{self._escape_xml(req.direccion_propietario)}</DireccionPropietario>" if req.direccion_propietario else "") +
            f"<TipoUsuarioPropietario>{req.tipo_usuario_propietario}</TipoUsuarioPropietario>"
            f"<TipoIdentificacionPropietario>{req.tipo_identificacion_propietario}</TipoIdentificacionPropietario>"
            f"<IdentificacionPropietario>{self._escape_xml(req.identificacion_propietario)}</IdentificacionPropietario>" +
            (f"<TelefonoContactoPropietario>{self._escape_xml(req.telefono_contacto_propietario)}</TelefonoContactoPropietario>" if req.telefono_contacto_propietario else "") +
            f"</SolicitudRegistroPositivo>"
        )
        xml_payload = self._build_xml(os.getenv("MSG_TYPE_REGISTRO_POSITIVO"), body, req.observaciones)
        return self._send_request(os.getenv("MSG_TYPE_REGISTRO_POSITIVO"), xml_payload)

    def registrar_negativo(self, req: RegistroNegativoRequest) -> SRTMResponse:
        body = (
            f"<SolicitudRegistroNegativo>"
            f"<Imei>{req.imei}</Imei>"
            f"<Tecnologia>01</Tecnologia>"
            f"<FechaReporte>{self._get_current_datetime()}</FechaReporte>" +
            (f"<NombreRazonSocialReporte>{self._escape_xml(req.nombre_reporte)}</NombreRazonSocialReporte>" if req.nombre_reporte else "") +
            (f"<TipoIdentificacionReporte>{self._escape_xml(req.tipo_identificacion_reporte)}</TipoIdentificacionReporte>" if req.tipo_identificacion_reporte else "") +
            (f"<IdentificacionReporte>{self._escape_xml(req.identificacion_reporte)}</IdentificacionReporte>" if req.identificacion_reporte else "") +
            (f"<DireccionReporte>{self._escape_xml(req.direccion_reporte)}</DireccionReporte>" if req.direccion_reporte else "") +
            (f"<TelefonoContactoReporte>{self._escape_xml(req.telefono_reporte)}</TelefonoContactoReporte>" if req.telefono_reporte else "") +
            (f"<DepartamentoReporte>{self._escape_xml(req.departamento_reporte)}</DepartamentoReporte>" if req.departamento_reporte else "") +
            (f"<CiudadReporte>{self._escape_xml(req.ciudad_reporte)}</CiudadReporte>" if req.ciudad_reporte else "") +
            f"<TipoReporte>{req.tipo_reporte}</TipoReporte>" +
            (f"<EmpleoViolencia>{req.empleo_violencia}</EmpleoViolencia>" if req.empleo_violencia is not None else "") +
            (f"<UtilizacionArmas>{req.utilizacion_armas}</UtilizacionArmas>" if req.utilizacion_armas is not None else "") +
            (f"<VictimaMenorEdad>{req.victima_menor_edad}</VictimaMenorEdad>" if req.victima_menor_edad is not None else "") +
            (f"<CorreoElectronico>{self._escape_xml(req.correo_electronico)}</CorreoElectronico>" if req.correo_electronico else "") +
            f"</SolicitudRegistroNegativo>"
        )
        xml_payload = self._build_xml(os.getenv("MSG_TYPE_REGISTRO_NEGATIVO"), body, req.observaciones)
        return self._send_request(os.getenv("MSG_TYPE_REGISTRO_NEGATIVO"), xml_payload)

    def cancelar_negativo(self, req: CancelacionNegativoRequest) -> SRTMResponse:
        """
        Procesa una solicitud de cancelación de registro negativo (3001).
        Utiliza la fecha_reporte proporcionada en el request en lugar de la fecha actual.
        
        Args:
            req (CancelacionNegativoRequest): Objeto con los datos de la cancelación
            
        Returns:
            SRTMResponse: Respuesta del servicio SOAP
        """
        body = (
            f"<SolicitudCancelacionRegistroNegativo>"
            f"<Imei>{req.imei}</Imei>"
            f"<FechaReporte>{req.fecha_reporte}</FechaReporte>"
            f"</SolicitudCancelacionRegistroNegativo>"
        )
        xml_payload = self._build_xml(os.getenv("MSG_TYPE_CANCELACION_NEGATIVO"), body, req.observaciones)
        return self._send_request(os.getenv("MSG_TYPE_CANCELACION_NEGATIVO"), xml_payload)

    def modificar_positivo(self, req: ModificacionPositivoRequest) -> SRTMResponse:
        # Construcción del cuerpo del XML para modificación, incluyendo campos de autorizado
        body = (
            f"<SolicitudModificacionRegistroPositivo>"
            f"<Imei>{req.imei}</Imei>" +
            (f"<Imsi>{self._escape_xml(req.imsi)}</Imsi>" if req.imsi else "") +
            (f"<Msisdn>{self._escape_xml(req.msisdn)}</Msisdn>" if req.msisdn else "") +
            (f"<NombreRazonSocialPropietario>{self._escape_xml(req.nombre_razon_social_propietario)}</NombreRazonSocialPropietario>") +
            (f"<DireccionPropietario>{self._escape_xml(req.direccion_propietario)}</DireccionPropietario>") +
            f"<TipoUsuarioPropietario>{req.tipo_usuario_propietario}</TipoUsuarioPropietario>"
            f"<TipoIdentificacionPropietario>{req.tipo_identificacion_propietario}</TipoIdentificacionPropietario>"
            f"<IdentificacionPropietario>{self._escape_xml(req.identificacion_propietario)}</IdentificacionPropietario>" +
            (f"<TelefonoContactoPropietario>{self._escape_xml(req.telefono_contacto_propietario)}</TelefonoContactoPropietario>") +
            # Campos de autorizado (se envían si existen)
            (f"<NombreRazonSocialAutorizado>{self._escape_xml(req.nombre_razon_social_autorizado)}</NombreRazonSocialAutorizado>" if req.nombre_razon_social_autorizado else "") +
            (f"<TipoUsuarioAutorizado>{req.tipo_usuario_autorizado}</TipoUsuarioAutorizado>" if req.tipo_usuario_autorizado else "") +
            (f"<TipoIdentificacionAutorizado>{req.tipo_identificacion_autorizado}</TipoIdentificacionAutorizado>" if req.tipo_identificacion_autorizado else "") +
            (f"<IdentificacionAutorizado>{self._escape_xml(req.identificacion_autorizado)}</IdentificacionAutorizado>" if req.identificacion_autorizado else "") +
            (f"<TelefonoContactoAutorizado>{self._escape_xml(req.telefono_contacto_autorizado)}</TelefonoContactoAutorizado>" if req.telefono_contacto_autorizado else "") +
            # Campos de propietario anterior
            (f"<TipoIdentificacionPropietarioAnterior>{self._escape_xml(req.tipo_identificacion_propietario_anterior)}</TipoIdentificacionPropietarioAnterior>" if req.tipo_identificacion_propietario_anterior else "") +
            (f"<IdentificacionPropietarioAnterior>{self._escape_xml(req.identificacion_propietario_anterior)}</IdentificacionPropietarioAnterior>" if req.identificacion_propietario_anterior else "") +
            f"<TipoModificacion>{req.tipo_modificacion}</TipoModificacion>"
            f"</SolicitudModificacionRegistroPositivo>"
        )
        xml_payload = self._build_xml(os.getenv("MSG_TYPE_MODIFICACION_POSITIVO"), body, req.observaciones)
        return self._send_request(os.getenv("MSG_TYPE_MODIFICACION_POSITIVO"), xml_payload)

    def cancelar_positivo(self, req: CancelacionPositivoRequest) -> SRTMResponse:
        body = (
            f"<SolicitudCancelacionRegistroPositivo>"
            f"<Imei>{req.imei}</Imei>"
            f"<TipoUsuarioPropietario>{req.tipo_usuario_propietario}</TipoUsuarioPropietario>"
            f"<TipoIdentificacionPropietario>{req.tipo_identificacion_propietario}</TipoIdentificacionPropietario>"
            f"<IdentificacionPropietario>{self._escape_xml(req.identificacion_propietario)}</IdentificacionPropietario>"
            f"</SolicitudCancelacionRegistroPositivo>"
        )
        xml_payload = self._build_xml(os.getenv("MSG_TYPE_CANCELACION_POSITIVO"), body, req.observaciones)
        return self._send_request(os.getenv("MSG_TYPE_CANCELACION_POSITIVO"), xml_payload)
