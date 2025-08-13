import logging
from flask import Flask, request, Response
from lxml import etree
import os

# --- Logger setup ---
if not os.path.exists('logs'):
    os.makedirs('logs')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('logs/webhook.log', mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = Flask(__name__)

# Diccionario para mapear el TipoMsg con el nombre del elemento de respuesta
MESSAGE_MAP = {
    '1002': 'RespuestaRegistroPositivo',
    '2002': 'RespuestaRegistroNegativo',
    '3002': 'RespuestaCancelacionRegistroNegativo',
    '4002': 'RespuestaModificacionRegistroPositivo',
    '5002': 'RespuestaCancelacionRegistroPositivo',
}

@app.route('/srtm_response', methods=['POST'])
def handle_srtm_response():
    """
    Handles incoming POST requests from the SRTM API.
    """
    logger.info("📡 Incoming request received on /srtm_response")

    # 1. Cambia la validación del Content-Type a 'application/xml'
    if request.content_type not in ['text/xml', 'application/xml']:
        logger.warning(f"⚠️ Invalid Content-Type: {request.content_type}. Expected 'text/xml' or 'application/xml'.")
        # 3. Contesta vacío el error si el formato es inválido
        return "", 404

    xml_data = request.data
    logger.info(f"📄 Raw XML data received:\n{xml_data.decode('utf-8')}")

    try:
        root = etree.fromstring(xml_data)
        
        # Define namespaces for XPath queries
        namespaces = {'xsd': 'http://www.w3.org/2001/XMLSchema'}
        tipo_msg_element = root.xpath(".//TipoMsg", namespaces=namespaces)
        
        # 4. Genera la validación para los mensajes 1002, 3002, 4002, 5002 y 2002
        if not tipo_msg_element or tipo_msg_element[0].text not in MESSAGE_MAP:
            logger.warning(f"⚠️ Received a message that is not a supported type. Ignoring.")
            return "", 200

        message_type = tipo_msg_element[0].text
        response_element_name = MESSAGE_MAP[message_type]

        # Use the mapped element name to find the response type
        xpath_query = f".//{response_element_name}/TipoRespuesta"
        tipo_respuesta_element = root.xpath(xpath_query, namespaces=namespaces)

        if tipo_respuesta_element:
            response_type = tipo_respuesta_element[0].text
            if response_type == '1':
                logger.info(f"✅ Received an 'Aceptada' response for message type {message_type}.")
            else:
                logger.warning(f"❌ Received a 'Rechazada' response for message type {message_type}.")
            
            logger.info(f"🎉 Successfully processed message type {message_type} transaction.")

            # --- CONSTRUIR LA RESPUESTA XML CON EL FORMATO SOLICITADO ---
            nsmap = {
                'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                'xsd': 'http://www.w3.org/2001/XMLSchema',
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            }
            soap_envelope = etree.Element(
                '{http://schemas.xmlsoap.org/soap/envelope/}Envelope', 
                nsmap=nsmap
            )
            soap_body = etree.SubElement(soap_envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Body')
            receive_message_response = etree.SubElement(soap_body, '{http://service.client.xcewsmulti.iecisa.es}receiveMessageResponse')
            receive_message_return = etree.SubElement(receive_message_response, '{http://service.client.xcewsmulti.iecisa.es}receiveMessageReturn')
            receive_message_return.text = 'ack'
            
            ack_response = etree.tostring(soap_envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

            logger.info(f"➡️ Sending 'ack' response:\n{ack_response.decode('utf-8')}")
            return Response(ack_response, mimetype='text/xml')

        else:
            logger.error(f"❌ Could not find the TipoRespuesta element for message type {message_type}.")
            # 3. Contesta vacío el error
            return "", 404

    except etree.XMLSyntaxError as e:
        logger.error(f"❌ Failed to parse XML: {e}", exc_info=True)
        # 3. Contesta vacío el error
        return "", 404
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}", exc_info=True)
        # 3. Contesta vacío el error
        return "", 500

if __name__ == '__main__':
    print("🚀 Starting SRTM Webhook...")
    # 2. Cambia el puerto a 6750
    print("🌍 Listening on http://localhost:6750/srtm_response")
    app.run(host='0.0.0.0', port=6750, debug=True)