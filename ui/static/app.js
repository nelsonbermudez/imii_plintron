// script.js - Cliente Web para SRTM API (VERSION COMPLETA CORREGIDA)

/**
 * Configuración de la API
 */
const API_CONFIG = {
    baseUrl: 'http://localhost:8000',
    timeout: 30000,
    corsMode: 'cors',
    endpoints: {
        registroPositivo: '/registro-positivo',
        registroNegativo: '/registro-negativo',
        cancelacionNegativo: '/cancelacion-negativo',
        modificacionPositivo: '/modificacion-positivo',
        cancelacionPositivo: '/cancelacion-positivo',
        consultaPositiva: '/consulta/positiva',
        consultaNegativa: '/consulta/negativa',
        consultaNegativaTipo: '/consulta/negativa/tipo-reporte'
    }
};

/**
 * Variables globales
 */
let welcomeSection, formsContainer, loadingOverlay;

/**
 * ========================================
 * INICIALIZACIÓN
 * ========================================
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando SRTM API Client...');
    
    try {
        initializeDOMReferences();
        initializeEventListeners();
        setupFormValidation();
        setupConditionalFields();
        setupAutoComplete();
        setupFormSubmissions();
        setupFechaReporteHandlers();
        
        // Hacer funciones disponibles globalmente
        window.clearResponseArea = clearResponseArea;
        
        console.log('✅ Inicialización completada');
    } catch (error) {
        console.error('❌ Error en la inicialización:', error);
    }
});

function initializeDOMReferences() {
    welcomeSection = document.getElementById('welcome-section');
    formsContainer = document.getElementById('forms-container');
    loadingOverlay = document.getElementById('loadingOverlay');
    
    if (!welcomeSection || !formsContainer || !loadingOverlay) {
        console.error('❌ No se encontraron elementos DOM necesarios');
    }
}

/**
 * ========================================
 * MANEJADORES DE FECHA REPORTE
 * ========================================
 */

function setupFechaReporteHandlers() {
    // Configurar el campo de fecha reporte
    const fechaReporteInput = document.querySelector('.fecha-reporte-input');
    const btnFechaActual = document.getElementById('btn-fecha-actual');
    const fechaPreview = document.getElementById('fecha-preview');
    
    if (fechaReporteInput) {
        // Evento para formatear y validar mientras escribe
        fechaReporteInput.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, ''); // Solo números
            
            // Limitar a 14 caracteres
            if (value.length > 14) {
                value = value.slice(0, 14);
            }
            
            this.value = value;
            
            // Mostrar preview si tiene 14 dígitos
            if (value.length === 14) {
                showFechaPreview(value, fechaPreview);
                validateFechaReporte(this, value);
            } else {
                hideFechaPreview(fechaPreview);
                this.classList.remove('is-valid', 'is-invalid');
            }
        });
        
        // Evento blur para validación final
        fechaReporteInput.addEventListener('blur', function() {
            if (this.value.length > 0) {
                validateFechaReporte(this, this.value);
            }
        });
    }
    
    // Botón para usar fecha actual
    if (btnFechaActual) {
        btnFechaActual.addEventListener('click', function() {
            if (fechaReporteInput) {
                const fechaActual = getCurrentDateTime();
                fechaReporteInput.value = fechaActual;
                showFechaPreview(fechaActual, fechaPreview);
                validateFechaReporte(fechaReporteInput, fechaActual);
                
                showToast('Fecha actual aplicada', 'info');
            }
        });
    }
}

function getCurrentDateTime() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    return `${year}${month}${day}${hours}${minutes}${seconds}`;
}

function parseFechaReporte(fechaStr) {
    if (fechaStr.length !== 14) return null;
    
    try {
        const year = parseInt(fechaStr.substr(0, 4));
        const month = parseInt(fechaStr.substr(4, 2));
        const day = parseInt(fechaStr.substr(6, 2));
        const hours = parseInt(fechaStr.substr(8, 2));
        const minutes = parseInt(fechaStr.substr(10, 2));
        const seconds = parseInt(fechaStr.substr(12, 2));
        
        // Crear fecha y validar
        const fecha = new Date(year, month - 1, day, hours, minutes, seconds);
        
        // Verificar que la fecha sea válida
        if (fecha.getFullYear() !== year || 
            fecha.getMonth() !== month - 1 || 
            fecha.getDate() !== day ||
            fecha.getHours() !== hours ||
            fecha.getMinutes() !== minutes ||
            fecha.getSeconds() !== seconds) {
            return null;
        }
        
        return fecha;
    } catch (error) {
        return null;
    }
}

function formatFechaReadable(fechaStr) {
    const fecha = parseFechaReporte(fechaStr);
    if (!fecha) return 'Fecha inválida';
    
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    
    return fecha.toLocaleDateString('es-ES', options);
}

function showFechaPreview(fechaStr, previewElement) {
    if (previewElement) {
        const fechaReadable = formatFechaReadable(fechaStr);
        const readableSpan = previewElement.querySelector('.fecha-readable');
        if (readableSpan) {
            readableSpan.textContent = fechaReadable;
            previewElement.style.display = 'block';
        }
    }
}

function hideFechaPreview(previewElement) {
    if (previewElement) {
        previewElement.style.display = 'none';
    }
}

function validateFechaReporte(input, fechaStr) {
    if (fechaStr.length !== 14) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        return false;
    }
    
    const fecha = parseFechaReporte(fechaStr);
    const ahora = new Date();
    
    if (!fecha) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        return false;
    }
    
    // Verificar que la fecha no sea futura
    if (fecha > ahora) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        showToast('La fecha del reporte no puede ser futura', 'warning');
        return false;
    }
    
    // Verificar que la fecha no sea muy antigua (más de 10 años)
    const diezAñosAtras = new Date();
    diezAñosAtras.setFullYear(diezAñosAtras.getFullYear() - 10);
    
    if (fecha < diezAñosAtras) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        showToast('La fecha del reporte es muy antigua (más de 10 años)', 'warning');
        return false;
    }
    
    input.classList.add('is-valid');
    input.classList.remove('is-invalid');
    return true;
}

/**
 * ========================================
 * EVENT LISTENERS
 * ========================================
 */

function initializeEventListeners() {
    // Navegación del menú
    document.querySelectorAll('[data-form]').forEach(link => {
        link.addEventListener('click', handleMenuClick);
    });

    // Botones de limpiar formularios
    document.querySelectorAll('.btn-clear').forEach(button => {
        button.addEventListener('click', handleClearForm);
    });

    // Atajos de teclado
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function handleMenuClick(e) {
    e.preventDefault();
    const formId = this.getAttribute('data-form');
    showForm(formId);
}

function handleClearForm() {
    const form = this.closest('form');
    if (form) {
        clearForm(form);
    }
}

function handleKeyboardShortcuts(e) {
    // Ctrl+L para limpiar formulario activo
    if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        const activeForm = document.querySelector('.form-section:not(.d-none) form');
        if (activeForm) {
            clearForm(activeForm);
        }
    }
}

/**
 * ========================================
 * ENVÍO DE FORMULARIOS
 * ========================================
 */

function setupFormSubmissions() {
    const formConfigs = [
        { id: 'registroPositivoForm', endpoint: 'registroPositivo', method: 'POST' },
        { id: 'registroNegativoForm', endpoint: 'registroNegativo', method: 'POST' },
        { id: 'cancelacionNegativoForm', endpoint: 'cancelacionNegativo', method: 'POST' },
        { id: 'modificacionPositivoForm', endpoint: 'modificacionPositivo', method: 'POST' },
        { id: 'cancelacionPositivoForm', endpoint: 'cancelacionPositivo', method: 'POST' },
        { id: 'consultaPositivaForm', endpoint: 'consultaPositiva', method: 'POST' },
        { id: 'consultaNegativaForm', endpoint: 'consultaNegativa', method: 'GET' },
        { id: 'consultaNegativaTipoForm', endpoint: 'consultaNegativaTipo', method: 'GET' }
    ];

    console.log('🔧 Configurando formularios:', formConfigs);

    formConfigs.forEach(config => {
        const form = document.getElementById(config.id);
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                handleFormSubmit(this, config.endpoint, config.method);
            });
        } else {
            console.warn(`⚠️ Formulario no encontrado: ${config.id}`);
        }
    });
}

async function handleFormSubmit(form, endpoint, method) {
    try {
        console.log(`📤 Enviando formulario: ${form.id}`);
        await submitForm(form, endpoint, method);
    } catch (error) {
        console.error('❌ Error en el envío del formulario:', error);
        showToast('Error al procesar el formulario', 'error');
    }
}

async function submitForm(form, endpoint, method) {
    if (!validateForm(form)) {
        showToast('Por favor, complete todos los campos requeridos correctamente', 'error');
        return;
    }

    showLoading(true);

    try {
        const formData = getFormData(form);
        const url = buildApiUrl(endpoint, method, formData);
        const options = buildRequestOptions(method, formData);

        console.log(`🌐 Enviando petición a: ${url}`);
        console.log(`📤 Método HTTP: ${method}`);
        console.log(`📋 Datos:`, formData);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);
        options.signal = controller.signal;

        const response = await fetch(url, options);
        clearTimeout(timeoutId);

        console.log(`📡 Status: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                errorData = { 
                    message: `HTTP ${response.status}: ${response.statusText}`,
                    details: await response.text()
                };
            }
            
            console.log(`❌ Error response:`, errorData);
            showResponseInTable({
                success: false,
                http_status: response.status,
                message: errorData.message || errorData.detail || `Error HTTP ${response.status}`,
                error_code: errorData.error_code || 'HTTP_ERROR',
                details: errorData.details || response.statusText,
                errors: errorData.errors || null,
                raw_response: errorData
            }, response.status, form.id);
            return;
        }

        let result;
        try {
            result = await response.json();
        } catch (e) {
            // Si no hay JSON válido pero el status es 200, considerarlo éxito
            result = {
                success: true,
                message: 'Operación completada exitosamente',
                http_status: response.status,
                details: 'Respuesta recibida sin contenido JSON'
            };
        }

        // Para status 200, siempre considerar como éxito, incluso si success es false o no existe
        if (response.status === 200) {
            result.success = true;
            result.http_status = 200;
            
            // Si no hay mensaje, agregar uno por defecto
            if (!result.message) {
                result.message = 'Operación completada exitosamente';
            }
            
            // Si no hay datos pero es 200, agregar mensaje informativo
            if (!result.raw_response || (Array.isArray(result.raw_response) && result.raw_response.length === 0)) {
                if (!result.raw_response) {
                    result.additional_info = 'La operación se completó correctamente pero no se retornaron datos adicionales.';
                } else {
                    result.additional_info = 'La consulta se ejecutó correctamente pero no se encontraron registros que coincidan con los criterios especificados.';
                }
            }
        }

        console.log(`📥 Respuesta recibida:`, result);
        showResponseInTable(result, response.status, form.id);

    } catch (error) {
        console.error('❌ Error completo:', error);
        
        let errorMessage = 'Error desconocido';
        let errorCode = 'UNKNOWN_ERROR';
        let corsHelp = '';
        let troubleshootingSteps = '';
        
        if (error.message.includes('CORS') || 
            error.message.includes('cors') ||
            error.message.includes('Access-Control-Allow-Origin') ||
            error.message.includes('blocked by CORS policy')) {
            
            errorMessage = '🚫 Error de CORS: El servidor no permite requests desde este origen';
            errorCode = 'CORS_ERROR';
            
            showToast('🚫 Error de CORS detectado - Revise las instrucciones en la tabla', 'error');
            
            corsHelp = buildCorsHelp();
            
        } else if (error.name === 'AbortError') {
            errorMessage = `⏰ Timeout: La solicitud tardó más de ${API_CONFIG.timeout/1000} segundos`;
            errorCode = 'TIMEOUT_ERROR';
            
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = '🔌 No se puede conectar con el servidor';
            errorCode = 'CONNECTION_ERROR';
            
            troubleshootingSteps = buildTroubleshootingSteps();
            
        } else {
            errorMessage = `❌ ${error.message}`;
        }
        
        const debugInfo = {
            error_name: error.name,
            error_message: error.message,
            frontend_origin: window.location.origin,
            api_url: API_CONFIG.baseUrl,
            endpoint: endpoint,
            method: method,
            timestamp: new Date().toISOString()
        };
        
        showResponseInTable({
            success: false,
            message: errorMessage,
            error_code: errorCode,
            details: error.message,
            cors_help: corsHelp,
            troubleshooting_steps: troubleshootingSteps,
            debug_info: debugInfo
        }, 500, form.id);
    } finally {
        showLoading(false);
    }
}

function buildApiUrl(endpoint, method, formData) {
    let url = API_CONFIG.baseUrl + API_CONFIG.endpoints[endpoint];
    
    if (method === 'GET' && formData.imei) {
        url += `/${formData.imei}`;
    }
    
    return url;
}

function buildRequestOptions(method, formData) {
    const options = {
        method: method,
        mode: API_CONFIG.corsMode,
        credentials: 'omit',
        redirect: 'follow'
    };

    if (method === 'GET') {
        options.headers = {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        };
    } else {
        options.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        };
        options.body = JSON.stringify(formData);
    }

    return options;
}

function buildCorsHelp() {
    return `
        <div class="mt-4 p-3 bg-danger bg-opacity-10 border border-danger rounded">
            <h6 class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Error de CORS Detectado</h6>
            <p class="mb-3"><strong>Problema:</strong> Su API Python no tiene configurado CORS para permitir requests desde <code>${window.location.origin}</code></p>
            
            <div class="bg-warning bg-opacity-25 p-3 rounded mb-3">
                <h6 class="text-warning mb-2"><i class="fas fa-tools me-2"></i>Solución Inmediata:</h6>
                <p class="mb-2"><strong>1.</strong> Agregue este código a su <code>main.py</code> DESPUÉS de <code>app = FastAPI(...)</code>:</p>
                <pre class="bg-dark text-light p-3 rounded" style="font-size: 0.85rem; overflow-x: auto;">
<span class="text-info"># Importar CORS</span>
from fastapi.middleware.cors import CORSMiddleware

<span class="text-info"># Agregar después de app = FastAPI(...)</span>
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:8080"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)</pre>
                <p class="mb-2 mt-3"><strong>2.</strong> Reinicie su servidor Python:</p>
                <pre class="bg-dark text-light p-2 rounded" style="font-size: 0.85rem;">
uvicorn main:app --host 0.0.0.0 --port 8000 --reload</pre>
                <p class="mb-0 mt-3"><strong>3.</strong> Recargue esta página y pruebe nuevamente</p>
            </div>
        </div>
    `;
}

function buildTroubleshootingSteps() {
    return `
        <div class="mt-3 p-3 bg-warning bg-opacity-10 border border-warning rounded">
            <h6 class="text-warning"><i class="fas fa-exclamation-triangle me-2"></i>Pasos de Diagnóstico:</h6>
            <ol class="mb-0">
                <li>Verifique que la API esté ejecutándose en <code>${API_CONFIG.baseUrl}</code></li>
                <li>Abra <a href="${API_CONFIG.baseUrl}/docs" target="_blank">${API_CONFIG.baseUrl}/docs</a> en una nueva pestaña</li>
                <li>Si no abre, inicie el servidor: <code>uvicorn main:app --host 0.0.0.0 --port 8000 --reload</code></li>
                <li>Verifique que no haya firewall bloqueando el puerto 8000</li>
            </ol>
        </div>
    `;
}

/**
 * ========================================
 * VALIDACIÓN DE FORMULARIOS
 * ========================================
 */

function setupFormValidation() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('input', function(e) {
            validateField(e.target);
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        validateField(field);
        if (field.classList.contains('is-invalid') || 
            (field.hasAttribute('required') && field.value.trim() === '')) {
            isValid = false;
        }
    });

    // Validación especial para fecha_reporte si existe
    const fechaReporteField = form.querySelector('[name="fecha_reporte"]');
    if (fechaReporteField && fechaReporteField.value.trim() !== '') {
        if (!validateFechaReporte(fechaReporteField, fechaReporteField.value)) {
            isValid = false;
        }
    }

    return isValid;
}

function validateField(field) {
    const value = field.value.trim();
    let isValid = true;

    if (field.hasAttribute('required') && value === '') {
        isValid = false;
    } else if (value !== '') {
        if (field.name === 'imei') {
            isValid = isValidIMEI(value);
        } else if (field.name === 'fecha_reporte') {
            isValid = validateFechaReporte(field, value);
            return; // validateFechaReporte ya maneja las clases CSS
        } else if (field.type === 'email') {
            isValid = isValidEmail(value);
        }
    }

    if (isValid && value !== '') {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
    } else if (!isValid) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
    } else {
        field.classList.remove('is-valid', 'is-invalid');
    }
}

/**
 * ========================================
 * FUNCIONES DE VALIDACIÓN
 * ========================================
 */

function isValidIMEI(imei) {
    // Verificar que sea exactamente 15 dígitos
    if (!/^[0-9]{15}$/.test(imei)) {
        return false;
    }
    
    // Algoritmo de Luhn para validar IMEI
    let sum = 0;
    for (let i = 0; i < 14; i++) {
        let digit = parseInt(imei[i]);
        if (i % 2 === 1) {
            digit *= 2;
            if (digit > 9) {
                digit = Math.floor(digit / 10) + (digit % 10);
            }
        }
        sum += digit;
    }
    
    const checkDigit = (10 - (sum % 10)) % 10;
    return checkDigit === parseInt(imei[14]);
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function formatPhoneNumber(phone) {
    const cleaned = phone.replace(/\D/g, '');
    
    if (cleaned.length === 10) {
        return cleaned.replace(/(\d{3})(\d{3})(\d{4})/, '$1 $2 $3');
    } else if (cleaned.length === 7) {
        return cleaned.replace(/(\d{3})(\d{4})/, '$1 $2');
    }
    
    return phone;
}

/**
 * ========================================
 * AUTO-COMPLETADO
 * ========================================
 */

function setupAutoComplete() {
    setupPhoneFormatting();
    setupIMEIValidation();
}

function setupPhoneFormatting() {
    document.querySelectorAll('input[name*="telefono"]').forEach(input => {
        input.addEventListener('input', function() {
            this.value = formatPhoneNumber(this.value);
        });
    });
}

function setupIMEIValidation() {
    document.querySelectorAll('input[name="imei"]').forEach(input => {
        input.addEventListener('input', function() {
            // Solo permitir números
            this.value = this.value.replace(/\D/g, '');
            
            // Limitar a 15 caracteres
            if (this.value.length > 15) {
                this.value = this.value.slice(0, 15);
            }
            
            // Validar IMEI si tiene 15 dígitos
            if (this.value.length === 15) {
                validateField(this);
            }
        });
    });
}

/**
 * ========================================
 * CAMPOS CONDICIONALES
 * ========================================
 */

function setupConditionalFields() {
    setupRegistroNegativoConditionals();
    setupModificacionPositivoConditionals();
}

function setupRegistroNegativoConditionals() {
    const tipoReporteSelect = document.querySelector('[name="tipo_reporte"]');
    if (tipoReporteSelect) {
        tipoReporteSelect.addEventListener('change', function() {
            const roboFields = document.getElementById('robo-fields');
            if (roboFields) {
                if (this.value === '1') {
                    roboFields.classList.remove('d-none');
                } else {
                    roboFields.classList.add('d-none');
                    clearRoboFields(roboFields);
                }
            }
        });
    }

    const empleoViolenciaSelect = document.querySelector('[name="empleo_violencia"]');
    if (empleoViolenciaSelect) {
        empleoViolenciaSelect.addEventListener('change', function() {
            const armasField = document.getElementById('armas-field');
            const menorField = document.getElementById('menor-field');
            
            if (this.value === '1') {
                if (armasField) armasField.style.display = 'block';
                if (menorField) menorField.style.display = 'block';
            } else {
                if (armasField) armasField.style.display = 'none';
                if (menorField) menorField.style.display = 'none';
                clearViolenciaFields();
            }
        });
    }
}

function setupModificacionPositivoConditionals() {
    const tipoModificacionSelect = document.querySelector('[name="tipo_modificacion"]');
    if (tipoModificacionSelect) {
        tipoModificacionSelect.addEventListener('change', function() {
            const propietarioAnteriorFields = document.getElementById('propietario-anterior-fields');
            if (propietarioAnteriorFields) {
                if (this.value === '2' || this.value === '3') {
                    propietarioAnteriorFields.classList.remove('d-none');
                } else {
                    propietarioAnteriorFields.classList.add('d-none');
                }
            }
        });
    }

    const tipoUsuarioAutorizadoSelect = document.querySelector('[name="tipo_usuario_autorizado"]');
    if (tipoUsuarioAutorizadoSelect) {
        tipoUsuarioAutorizadoSelect.addEventListener('change', function() {
            const autorizadoFields = document.getElementById('autorizado-fields');
            if (autorizadoFields) {
                if (this.value !== '0' && this.value !== '') {
                    autorizadoFields.classList.remove('d-none');
                } else {
                    autorizadoFields.classList.add('d-none');
                }
            }
        });
    }
}

function clearRoboFields(roboFields) {
    roboFields.querySelectorAll('select').forEach(select => {
        select.value = '';
    });
}

function clearViolenciaFields() {
    const utilizacionArmas = document.querySelector('[name="utilizacion_armas"]');
    const victimaMenor = document.querySelector('[name="victima_menor_edad"]');
    
    if (utilizacionArmas) utilizacionArmas.value = '';
    if (victimaMenor) victimaMenor.value = '';
}

/**
 * ========================================
 * NAVEGACIÓN Y UI
 * ========================================
 */

function showForm(formId) {
    if (welcomeSection) {
        welcomeSection.style.display = 'none';
    }
    
    document.querySelectorAll('.form-section').forEach(section => {
        section.classList.add('d-none');
    });
    
    const targetForm = document.getElementById(`form-${formId}`);
    if (targetForm) {
        targetForm.classList.remove('d-none');
        targetForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
        console.log(`📋 Mostrando formulario: ${formId}`);
    }
}

function clearForm(form) {
    form.reset();
    
    form.querySelectorAll('.is-valid, .is-invalid').forEach(element => {
        element.classList.remove('is-valid', 'is-invalid');
    });
    
    hideConditionalFields(form);
    clearResponseArea(form.id);
    
    // Limpiar preview de fecha si existe
    const fechaPreview = form.querySelector('#fecha-preview');
    if (fechaPreview) {
        hideFechaPreview(fechaPreview);
    }
    
    showToast('Formulario limpiado correctamente', 'success');
    console.log(`🧹 Formulario limpiado: ${form.id}`);
}

function clearResponseArea(formId) {
    const responseArea = document.getElementById(`response-${formId}`);
    if (responseArea) {
        responseArea.style.display = 'none';
        responseArea.classList.remove('show');
    }
}

function hideConditionalFields(form) {
    const conditionalSelectors = [
        '#robo-fields',
        '#armas-field',
        '#menor-field',
        '#propietario-anterior-fields',
        '#autorizado-fields'
    ];
    
    conditionalSelectors.forEach(selector => {
        const element = form.querySelector(selector);
        if (element) {
            element.classList.add('d-none');
            element.style.display = 'none';
        }
    });
}

/**
 * ========================================
 * RESPUESTAS DE LA API
 * ========================================
 */

function showResponseInTable(response, statusCode, formId) {
    const responseArea = document.getElementById(`response-${formId}`);
    const responseContent = responseArea?.querySelector('.response-content');
    
    if (!responseArea || !responseContent) {
        console.error(`❌ Área de respuesta no encontrada para: ${formId}`);
        return;
    }

    // Determinar si es éxito basado en status code Y campo success
    let isSuccess;
    if (statusCode === 200 || statusCode === 201) {
        // Para códigos 2xx, siempre considerar como éxito
        isSuccess = true;
    } else if (statusCode >= 400) {
        // Para códigos 4xx y 5xx, siempre considerar como error
        isSuccess = false;
    } else {
        // Para otros códigos, usar el campo success de la respuesta
        isSuccess = response.success === true;
    }
    
    const responseClass = isSuccess ? 'response-success' : 'response-error';
    
    responseContent.innerHTML = '';
    responseArea.className = `response-area mt-4 ${responseClass}`;
    
    const tableHtml = buildResponseTable(response, statusCode, isSuccess, formId);
    responseContent.innerHTML = tableHtml;
    
    responseArea.style.display = 'block';
    responseArea.classList.add('show');
    responseArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    console.log(`📊 Respuesta mostrada en tabla para: ${formId} - Éxito: ${isSuccess}`);
}

function buildResponseTable(response, statusCode, isSuccess, formId) {
    // Determinar el badge y mensaje apropiado
    let statusBadge, defaultMessage;
    
    if (statusCode === 200 || statusCode === 201) {
        statusBadge = '<span class="status-badge status-success"><i class="fas fa-check-circle me-1"></i>OK</span>';
        defaultMessage = 'Operación completada exitosamente';
    } else if (statusCode >= 400) {
        statusBadge = '<span class="status-badge status-error"><i class="fas fa-exclamation-triangle me-1"></i>Error</span>';
        defaultMessage = 'Error en la operación';
    } else {
        statusBadge = isSuccess ? 
            '<span class="status-badge status-success"><i class="fas fa-check-circle me-1"></i>Éxito</span>' :
            '<span class="status-badge status-error"><i class="fas fa-exclamation-triangle me-1"></i>Error</span>';
        defaultMessage = isSuccess ? 'Operación exitosa' : 'Error en la operación';
    }
    
    let mainContent = `
        <div class="response-table">
            <div class="table-responsive">
                <table class="table table-striped mb-0">
                    <thead>
                        <tr>
                            <th colspan="2">
                                ${isSuccess ? 
                                    '<i class="fas fa-check-circle me-2"></i>Resultado de la Operación' : 
                                    '<i class="fas fa-exclamation-triangle me-2"></i>Error en la Operación'
                                }
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th class="col-4 col-md-3">Estado</th>
                            <td class="col-8 col-md-9">${statusBadge}</td>
                        </tr>
                        <tr>
                            <th class="col-4 col-md-3">Código HTTP</th>
                            <td class="col-8 col-md-9"><code>${response.http_status || statusCode}</code></td>
                        </tr>
                        <tr>
                            <th class="col-4 col-md-3">Mensaje</th>
                            <td class="col-8 col-md-9"><div class="text-break">${escapeHtml(response.message || defaultMessage)}</div></td>
                        </tr>
    `;
    
    // Agregar información adicional para respuestas 200 sin datos
    if (response.additional_info) {
        mainContent += `
            <tr>
                <th class="col-4 col-md-3">Información</th>
                <td class="col-8 col-md-9">
                    <div class="text-break text-muted">
                        <i class="fas fa-info-circle me-1"></i>
                        ${escapeHtml(response.additional_info)}
                    </div>
                </td>
            </tr>
        `;
    }
    
    if (response.error_code) {
        mainContent += `
            <tr>
                <th class="col-4 col-md-3">Código Error</th>
                <td class="col-8 col-md-9"><span class="error-code">${escapeHtml(response.error_code)}</span></td>
            </tr>
        `;
    }
    
    if (response.transaction_timestamp) {
        mainContent += `
            <tr>
                <th class="col-4 col-md-3">Timestamp</th>
                <td class="col-8 col-md-9">
                    <small class="text-muted">
                        <i class="fas fa-clock me-1"></i>
                        <span class="d-block d-md-inline">${escapeHtml(response.transaction_timestamp)}</span>
                    </small>
                </td>
            </tr>
        `;
    }
    
    mainContent += `
                    </tbody>
                </table>
            </div>
            <div class="text-end p-2">
                <button type="button" class="btn btn-sm btn-outline-secondary clear-response-btn" onclick="clearResponseArea('${formId}')">
                    <i class="fas fa-times me-1"></i><span class="d-none d-md-inline">Limpiar Respuesta</span>
                </button>
            </div>
        </div>
    `;
    
    let additionalContent = '';
    
    if (response.errors && Array.isArray(response.errors)) {
        additionalContent += buildValidationErrorsTable(response.errors);
    }
    
    if (response.raw_response) {
        // Para respuestas exitosas, mostrar los datos con estilo positivo
        if (isSuccess) {
            additionalContent += buildSuccessDataTable(response.raw_response);
        } else {
            additionalContent += buildRawResponseTable(response.raw_response);
        }
    }
    
    if (response.cors_help) {
        additionalContent += response.cors_help;
    }
    
    if (response.troubleshooting_steps) {
        additionalContent += response.troubleshooting_steps;
    }
    
    if (response.debug_info && response.debug_info.frontend_origin) {
        additionalContent += buildDebugInfoSection(response.debug_info);
    }
    
    return mainContent + additionalContent;
}

function buildValidationErrorsTable(errors) {
    const errorRows = errors.map(error => `
        <tr>
            <td class="text-break">
                <i class="fas fa-times-circle text-danger me-2"></i>
                ${escapeHtml(error)}
            </td>
        </tr>
    `).join('');
    
    return `
        <div class="mt-3">
            <div class="response-table">
                <div class="table-responsive">
                    <table class="table table-striped mb-0">
                        <thead>
                            <tr>
                                <th><i class="fas fa-exclamation-triangle me-2"></i>Errores de Validación</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${errorRows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

function buildSuccessDataTable(rawResponse) {
    if (!rawResponse) return '';
    
    let content = '';
    
    if (Array.isArray(rawResponse)) {
        if (rawResponse.length === 0) {
            content = `
                <div class="text-center p-3 bg-success bg-opacity-10 border border-success rounded">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <span class="text-success">La consulta se ejecutó correctamente pero no se encontraron registros.</span>
                </div>
            `;
        } else {
            content = rawResponse.map(item => {
                if (typeof item === 'object') {
                    return buildSuccessObjectDataTable(item);
                }
                return `<div class="text-break p-2 bg-success bg-opacity-10 rounded">${escapeHtml(String(item))}</div>`;
            }).join('');
        }
    } else if (typeof rawResponse === 'object') {
        content = buildSuccessObjectDataTable(rawResponse);
    } else {
        content = `<div class="text-break p-2 bg-success bg-opacity-10 rounded">${escapeHtml(String(rawResponse))}</div>`;
    }
    
    return `
        <div class="mt-3">
            <h6 class="text-success"><i class="fas fa-database me-2"></i>Datos de Respuesta</h6>
            ${content}
        </div>
    `;
}

function buildSuccessObjectDataTable(obj) {
    const rows = Object.entries(obj).map(([key, value]) => `
        <tr class="table-success">
            <th class="col-4 col-md-3 text-break">${escapeHtml(key)}</th>
            <td class="col-8 col-md-9 text-break">${escapeHtml(String(value))}</td>
        </tr>
    `).join('');
    
    return `
        <div class="response-table mb-3">
            <div class="table-responsive">
                <table class="table table-sm table-striped mb-0">
                    <thead class="table-success">
                        <tr>
                            <th colspan="2" class="text-success">
                                <i class="fas fa-check-circle me-2"></i>Datos Encontrados
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function buildRawResponseTable(rawResponse) {
    if (!rawResponse) return '';
    
    let content = '';
    
    if (Array.isArray(rawResponse)) {
        content = rawResponse.map(item => {
            if (typeof item === 'object') {
                return buildObjectDataTable(item);
            }
            return `<div class="text-break p-2">${escapeHtml(String(item))}</div>`;
        }).join('');
    } else if (typeof rawResponse === 'object') {
        content = buildObjectDataTable(rawResponse);
    } else {
        content = `<div class="text-break p-2">${escapeHtml(String(rawResponse))}</div>`;
    }
    
    return `
        <div class="mt-3">
            <h6><i class="fas fa-database me-2"></i>Datos de Respuesta</h6>
            ${content}
        </div>
    `;
}

function buildObjectDataTable(obj) {
    const rows = Object.entries(obj).map(([key, value]) => `
        <tr>
            <th class="col-4 col-md-3 text-break">${escapeHtml(key)}</th>
            <td class="col-8 col-md-9 text-break">${escapeHtml(String(value))}</td>
        </tr>
    `).join('');
    
    return `
        <div class="response-table mb-3">
            <div class="table-responsive">
                <table class="table table-sm table-striped mb-0">
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function buildDebugInfoSection(debugInfo) {
    return `
        <div class="mt-3">
            <details class="debug-collapsible">
                <summary class="btn btn-outline-secondary btn-sm w-100">
                    <i class="fas fa-bug me-2"></i>Información Técnica
                </summary>
                <div class="debug-content mt-2">
                    <div class="table-responsive">
                        <table class="table table-sm table-striped mb-0">
                            <tbody>
                                <tr>
                                    <th class="col-4">Origen</th>
                                    <td class="col-8 text-break">${escapeHtml(debugInfo.frontend_origin || 'N/A')}</td>
                                </tr>
                                <tr>
                                    <th class="col-4">API URL</th>
                                    <td class="col-8 text-break">${escapeHtml(debugInfo.api_url || 'N/A')}</td>
                                </tr>
                                <tr>
                                    <th class="col-4">Método</th>
                                    <td class="col-8">${escapeHtml(debugInfo.method || 'N/A')}</td>
                                </tr>
                                <tr>
                                    <th class="col-4">Endpoint</th>
                                    <td class="col-8 text-break">${escapeHtml(debugInfo.endpoint || 'N/A')}</td>
                                </tr>
                                <tr>
                                    <th class="col-4">Timestamp</th>
                                    <td class="col-8 text-break">${escapeHtml(debugInfo.timestamp || 'N/A')}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </details>
        </div>
    `;
}

/**
 * ========================================
 * UTILIDADES
 * ========================================
 */

function getFormData(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        const trimmedValue = value.trim();
        if (trimmedValue !== '') {
            data[key] = trimmedValue;
        }
    }
    
    return data;
}

function showLoading(show) {
    if (loadingOverlay) {
        if (show) {
            loadingOverlay.classList.remove('d-none');
        } else {
            loadingOverlay.classList.add('d-none');
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * ========================================
 * TOASTS Y NOTIFICACIONES
 * ========================================
 */

function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    const toastId = 'toast-' + Date.now();
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${getBootstrapColor(type)} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${getToastIcon(type)} me-2"></i>
                    ${escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
    }
    return container;
}

function getBootstrapColor(type) {
    const colors = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return colors[type] || 'info';
}

function getToastIcon(type) {
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-triangle',
        'warning': 'fa-exclamation-circle',
        'info': 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

/**
 * ========================================
 * EVENTOS GLOBALES
 * ========================================
 */

window.addEventListener('load', function() {
    console.log('📱 SRTM API Client cargado completamente');
    console.log('🔧 Configuración API:', API_CONFIG);
    console.log('📋 Formularios detectados:', document.querySelectorAll('form').length);
    
    showLoading(false);
    showToast('Cliente SRTM API cargado. Use el menú para acceder a los formularios.', 'info');
    
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});