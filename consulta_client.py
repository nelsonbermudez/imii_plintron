# consulta_client.py
import logging
import os
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict

import requests
from lxml import etree

logger = logging.getLogger(__name__)

@dataclass
class ConsultaDBAResponse:
    success: bool = False
    http_status: int = 500
    response_time_ms: float = 0.0
    message: Optional[str] = "An internal error occurred."
    error_code: Optional[str] = None
    raw_response: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ConsultaDBAClient:
    def __init__(self, endpoint: str, user_id: str, password: str):
        if not all([endpoint, user_id, password]):
            raise ValueError("Endpoint, User ID, and Password must be provided.")
        self.endpoint = endpoint
        self.user_id = user_id
        self.password = password
        self.session = requests.Session()
        logger.info("🔧 Cliente ConsultaBDA (Modo Manual) inicializado.")

    def _build_negativa_query_xml(self, imei: str) -> str:
        """Construye el XML para consultas a la BDA Negativa."""
        return (
            '<![CDATA[<?xml version="1.0" encoding="UTF-8"?>'
            '<ConsultaBDA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<CuerpoConsulta><Consulta>'
            '<TipoConsulta>1</TipoConsulta>'
            f'<DatoConsulta>{imei}</DatoConsulta>'
            '</Consulta></CuerpoConsulta></ConsultaBDA>]]>'
        )

    def _build_positiva_query_xml(self, imei: str, tipo_id: str, id_prop: str) -> str:
        """Construye el XML para la consulta a la BDA Positiva."""
        return (
            '<![CDATA[<?xml version="1.0" encoding="UTF-8"?>'
            '<ConsultaBDA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<CuerpoConsulta><ConsultaPositiva>'
            f'<Imei>{imei}</Imei>'
            f'<TipoIdentificacionPropietario>{tipo_id}</TipoIdentificacionPropietario>'
            f'<IdentificacionPropietario>{id_prop}</IdentificacionPropietario>'
            '</ConsultaPositiva></CuerpoConsulta></ConsultaBDA>]]>'
        )

    def _send_request(self, query_operation_name: str, xml_payload: str) -> ConsultaDBAResponse:
        transaction_time = datetime.utcnow()
        response = ConsultaDBAResponse(timestamp=transaction_time)
        start_time = time.time()

        soap_envelope = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.consultabda.srtm.iecisa.co">
   <soapenv:Header/>
   <soapenv:Body>
      <ser:{query_operation_name}>
         <ser:usuario>{self.user_id}</ser:usuario>
         <ser:password>{self.password}</ser:password>
         <ser:xml>{xml_payload}</ser:xml>
      </ser:{query_operation_name}>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '""'}
        logger.info(f"--- INICIO CONSULTA ({query_operation_name}) ---")
        
        try:
            http_res = self.session.post(self.endpoint, data=soap_envelope.encode('utf-8'), headers=headers, timeout=30)
            response.http_status = http_res.status_code
            logger.info(f"Respuesta SOAP cruda del servicio:\n{http_res.text}")
            http_res.raise_for_status()
            
            root = etree.fromstring(http_res.content)
            result_element = root.find(f'.//{{*}}{query_operation_name}Return')

            if result_element is not None and result_element.text:
                inner_xml_root = etree.fromstring(result_element.text.encode('utf-8'))
                
                # --- LÓGICA DE PARSEO GENERALIZADA ---
                error_node = inner_xml_root.find('.//{*}RespuestaConsultaBDAError')
                registro_neg_node = inner_xml_root.find('.//{*}RegistroBDANegativa')
                # Asumimos una estructura para el registro positivo exitoso
                registro_pos_node = inner_xml_root.find('.//{*}RegistroBDAPositiva')
                
                if error_node is not None:
                    # Manejo de respuesta de error
                    response.success = False
                    codigo_error = error_node.findtext('{*}CodigoError', 'N/A')
                    desc_error = error_node.findtext('{*}DescripcionError', 'Error desconocido')
                    response.message = f"Error de la BDA: {desc_error}"
                    response.error_code = codigo_error
                    response.raw_response = [{"CodigoError": codigo_error, "DescripcionError": desc_error}]
                
                elif registro_neg_node is not None:
                    # Manejo de respuesta negativa exitosa
                    fecha_reporte_raw = registro_neg_node.findtext('{*}FechaReporte', '')
                    dt_obj = datetime.strptime(fecha_reporte_raw, '%Y%m%d%H%M%S') if fecha_reporte_raw else None
                    
                    response.success = True
                    response.message = "Consulta negativa procesada exitosamente."
                    response.raw_response = [{
                        "TipoRespuesta": inner_xml_root.findtext('.//{*}TipoRespuesta', 'N/A'),
                        "RespuestaConsultaBDANegativa": "Registro Encontrado",
                        "Imei": registro_neg_node.findtext('{*}Imei', 'N/A'),
                        "Tecnologia": registro_neg_node.findtext('{*}Tecnologia', 'N/A'),
                        "FechaReporte": dt_obj.strftime('%Y-%d-%m %H:%M:%S') if dt_obj else 'N/A'
                    }]

                elif registro_pos_node is not None:
                     # TODO: Implementar parseo de consulta positiva exitosa si se conoce la estructura
                     response.success = True
                     response.message = "Consulta positiva procesada exitosamente (Estructura de datos pendiente)."
                     response.raw_response = [{"status": "Registro Positivo Encontrado", "data": "..."}]

                else:
                    response.success = False
                    response.message = "La estructura de la respuesta no coincide con los patrones conocidos."
                    response.raw_response = [{"error": "Estructura de respuesta desconocida", "response_body": result_element.text}]

            else:
                response.success = False
                response.message = "La consulta no retornó resultados."
                response.raw_response = [{"error": "Tag de retorno vacío o no encontrado."}]

        except Exception as e:
            logger.error(f"Error inesperado en consulta ({query_operation_name}): {e}", exc_info=True)
            response.message = "Error inesperado en el procesamiento."
            response.http_status = 500
        
        finally:
            response.response_time_ms = (time.time() - start_time) * 1000
            logger.info(f"--- FIN CONSULTA ({query_operation_name}) --- | Éxito: {response.success}")

        return response

    def consulta_positiva(self, imei: str, tipo_id_propietario: str, id_propietario: str) -> ConsultaDBAResponse:
        xml_payload = self._build_positiva_query_xml(imei, tipo_id_propietario, id_propietario)
        return self._send_request('consultaBDAPositiva', xml_payload)

    def consulta_negativa(self, imei: str) -> ConsultaDBAResponse:
        xml_payload = self._build_negativa_query_xml(imei)
        return self._send_request('consultaBDANegativa', xml_payload)
        
    def consulta_negativa_tipo_reporte(self, imei: str) -> ConsultaDBAResponse:
        xml_payload = self._build_negativa_query_xml(imei) # Reutiliza el XML de consulta negativa
        return self._send_request('consultaBDANegativaTipoReporte', xml_payload)