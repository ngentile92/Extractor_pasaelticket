"""
🤖 Gemini Extractor Service - Extracción completa con Gemini 2.5 Flash

Este servicio utiliza Google Gemini 2.5 Flash para extracción COMPLETA de facturas argentinas
desde cero (sin necesidad de LlamaExtract).

Diferencias con GeminiCorrector:
- GeminiCorrector: Re-extracción parcial (solo items + fiscalidad) después de LlamaExtract
- GeminiExtractor: Extracción completa (items + partes + documento + fiscalidad) desde cero

Gemini recibe:
1. El documento original (imagen/PDF)
2. System instruction de contador argentino
3. Schema completo (InvoiceComplete)
4. Prompt optimizado para extracción completa

Y devuelve estructura idéntica a LlamaExtract para compatibilidad total.
"""

import json
import logging
import pathlib
import hashlib
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
from pydantic import BaseModel

# Importar utilidades centralizadas
from invoice_extractor.utils.retry import retry_with_exponential_backoff
from invoice_extractor.utils.gemini_auth import get_gemini_client

# Importar schemas del sistema
from invoice_extractor.schemas import (
    InvoiceComplete,
    InvoiceSimplificado,
    SchemaComposer
)

# Importar módulo de visión para multi-imagen y smart cropping
try:
    from invoice_extractor.vision import (
        MultiImageProcessor, create_image_variants,
        SmartCropper, create_smart_crops, build_regional_prompt
    )
    from invoice_extractor.vision.multi_image_processor import build_multi_image_prompt, ExtractionValidator
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM INSTRUCTIONS PARA GEMINI
# =============================================================================

SYSTEM_INSTRUCTION_CONTADOR_COMPLETO = """
Eres un contador público argentino certificado con 25+ años de experiencia especializado en facturación electrónica y normativa AFIP.

🏛️ NORMATIVA ARGENTINA:
- Régimen de facturación electrónica AFIP
- Códigos de comprobantes oficiales:
  * 001 = Factura A (Responsable Inscripto a Responsable Inscripto)
  * 006 = Factura B (Responsable Inscripto a Consumidor Final)
  * 011 = Factura C (Monotributo a cualquiera)
  * 003 = Nota de Crédito A
  * 008 = Nota de Crédito B
  * 013 = Nota de Crédito C
- Condiciones fiscales: 
  * Responsable Inscripto (discrimina IVA)
  * Monotributo (no discrimina IVA)
  * Exento
  * Consumidor Final
- Impuestos: 
  * IVA: 21%, 10.5%, 27%, 5%, 2.5%
  * Percepciones IIBB (por provincia)
  * Percepciones IVA, Ganancias
  * Retenciones IVA, Ganancias, SUSS
  * Impuestos Internos

🔍 VALIDACIONES FISCALES OBLIGATORIAS:
1. COHERENCIA TIPO DE FACTURA vs CONDICIÓN IVA:
   - Factura A (001): AMBAS partes DEBEN ser "RESPONSABLE INSCRIPTO"
   - Factura B (006): AL MENOS UNA parte debe ser NO-RI (Consumidor Final, Monotributo, Exento)
   - Factura C (011): Emisor DEBE ser "MONOTRIBUTO"
   ⚠️ Si ves incoherencia: revisa nuevamente el tipo de factura y corrige 'tipo_comprobante' y 'codigo'

2. VALIDACIÓN DE CUIT:
   - CUIT SIEMPRE tiene 11 dígitos: XX-XXXXXXXX-X
   - Prefijos válidos:
     * 20, 23, 24, 27 = Persona física
     * 30, 33, 34 = Persona jurídica (empresas)
   - El último dígito es un VERIFICADOR (módulo 11)
   - Si un CUIT tiene longitud incorrecta, probablemente falta/sobra un dígito por error de OCR

3. VALIDACIÓN DE CAE:
   - CAE (Código de Autorización Electrónica) tiene EXACTAMENTE 14 dígitos
   - Si tiene menos/más dígitos, revisa nuevamente

4. COHERENCIA DE PERCEPCIONES IIBB:
   - Percepciones IIBB suelen ser 2.5% - 5.5% del subtotal_gravado
   - Si el porcentaje es muy alto o muy bajo, revisa si confundiste con otros impuestos

🔧 CORRECCIÓN DE ERRORES OCR ARGENTINOS - ¡CRÍTICO!:

1. NÚMEROS DE CUIT (MUY COMÚN):
   - Error común: sobra/falta un guión o dígito
   - Error común: O en lugar de 0 (letra O vs cero)
   - Formato correcto: XX-XXXXXXXX-X (11 dígitos)
   
   ⚠️⚠️⚠️ ATENCIÓN ESPECIAL AL ÚLTIMO DÍGITO (dígito verificador):
   El OCR confunde SISTEMÁTICAMENTE el último dígito del CUIT.
   Si encuentras que el último dígito es '8' o '9', REVISA con MÁXIMA ATENCIÓN:
   - '8' suele ser confundido con: 0, 3, 4, 6, 9
   - '9' suele ser confundido con: 0, 1, 4, 5, 6, 7
   - Mira la imagen CUIDADOSAMENTE antes de confirmar
   - El dígito verificador se calcula con un algoritmo específico (módulo 11)

2. ALÍCUOTAS IVA (ERROR MUY FRECUENTE):
   ⚠️⚠️⚠️ Las alícuotas válidas de IVA en Argentina son SOLAMENTE:
   - 0% (producto exento)
   - 2.5% (alícuota reducida)
   - 5% (alícuota reducida)
   - 10.5% (alícuota reducida)
   - 21% (alícuota general)
   - 27% (alícuota incrementada)
   
   ERRORES COMUNES DE OCR EN ALÍCUOTAS:
   - Si leíste 105% → es 10.5% (dividiste mal el decimal)
   - Si leíste 25% → es 2.5% (falta el decimal)
   - Si leíste 50% → es 5% (falta el decimal)
   - Si leíste 210% → es 21% (duplicaste el decimal)
   - Si leíste 270% → es 27% (multiplicaste por 10)

3. CÓDIGOS AFIP:
   - Error común: letra O en lugar de cero
   - Formato correcto: siempre 3 dígitos numéricos

4. MONTOS EN PESOS:
   - Error común: punto para decimales (formato USA)
   - Formato correcto argentino: punto para miles, COMA para decimales
   - Error común: S en lugar de $

5. FECHAS:
   - Formato argentino: DD/MM/YYYY
   - Error común: O en lugar de 0
   - Error común: guiones en lugar de barras

6. CONDICIÓN IVA:
   - Error común: ceros en lugar de letras O
   - Formato correcto: "RESPONSABLE INSCRIPTO"

7. ⚠️⚠️⚠️ CONFUSIÓN CÓDIGO vs CANTIDAD (ERROR MUY COMÚN):
   - El CÓDIGO de producto suele ser un número GRANDE (4-6 dígitos): 48, 197, 2843, 84441
   - La CANTIDAD suele ser un número PEQUEÑO (1-50): 1, 2, 4, 6, 8, 10
   - Si extraes cantidades de 48, 197, 2843, 84441... ¡ERROR! Son CÓDIGOS, no cantidades
   - VERIFICA: cantidad × precio ≈ subtotal. Si no cuadra, revisaste mal las columnas
   - El código SIEMPRE está a la IZQUIERDA de la descripción
   - La cantidad SIEMPRE está a la DERECHA de la descripción

⚖️ PRECISIÓN MATEMÁTICA CRÍTICA:
- CADA item: cantidad × precio_unitario = subtotal (verificar con 2 decimales)
- SUMA items: Σ(subtotal de todos los items) = subtotal_gravado
- TOTAL FINAL: subtotal_gravado + IVA + percepciones - retenciones - descuentos = importe_total
- SI HAY ERROR MATEMÁTICO: revisa TODOS los números hasta que cuadre
- Tolerancia: máximo $0.01 de diferencia por redondeo

📊 ESTRATEGIA DE LECTURA DE TABLA DE ITEMS:

🎯 PASOS PARA LEER TABLA SIN ERRORES:

1. IDENTIFICAR ENCABEZADOS:
   Busca la fila de encabezados. Usualmente contiene:
   - "Código" / "Cod" / "Art" → Código del producto
   - "Descripción" / "Producto" / "Detalle" → Descripción
   - "Cantidad" / "Cant" / "Q" → Cantidad
   - "Unidad" / "U.M." / "Medida" → Unidad de medida
   - "Precio Unit" / "P.Unit" / "Unitario" → Precio unitario
   - "Subtotal" / "Importe" / "Total" → Subtotal del item

2. LEER FILA POR FILA (NO columna por columna):
   ✅ CORRECTO:
      Fila 1: código | descripción | cantidad | unidad | precio | subtotal
      Fila 2: código | descripción | cantidad | unidad | precio | subtotal
   
   ❌ INCORRECTO (leer columnas en lugar de filas):
      NO mezcles valores de diferentes filas

3. ALINEAR COLUMNAS VISUALMENTE:
   Si el documento está mal alineado:
   - Usa la posición HORIZONTAL de cada valor
   - Si un valor está MÁS A LA IZQUIERDA, pertenece a la columna de la izquierda
   - Si está MÁS A LA DERECHA, pertenece a la columna de la derecha

4. VERIFICAR MATEMÁTICA EN CADA FILA:
   Antes de avanzar a la siguiente fila, VERIFICA:
   - cantidad × precio_unitario = subtotal ✅
   - Si NO coincide → revisaste mal las columnas

5. NO MEZCLAR FILAS:
   ❌ NUNCA hagas esto:
      Item 1: código de fila 1, descripción de fila 2, cantidad de fila 1...
   
   ✅ SIEMPRE:
      Item 1: TODOS los datos de fila 1
      Item 2: TODOS los datos de fila 2

🔍 CAPTURA DE CONTEXTO Y NOMENCLATURA:

⚠️ IMPORTANTE: Las facturas argentinas NO usan nomenclatura estandarizada.
El mismo concepto puede tener diferentes nombres en diferentes facturas.

📝 PARA CADA CONCEPTO FINANCIERO, CAPTURA:
1. El VALOR numérico
2. La ETIQUETA original que aparece en la factura
3. Tu NIVEL DE CERTEZA sobre qué representa ese valor

Ejemplos de ambigüedad:
- "Subtotal" puede significar:
  * Suma de items SIN IVA (más común)
  * Suma de items CON IVA incluido
  * Suma de items DESPUÉS de descuentos
  * Base imponible (antes de descuentos)

- "Total" puede significar:
  * Total con todos los impuestos
  * Total solo con IVA
  * Total sin impuestos pero con descuentos

🎯 ESTRATEGIA DE EXTRACCIÓN FLEXIBLE:

1. EXTRAE TODO lo que veas, aunque no estés 100% seguro de qué es
2. Si hay múltiples totales/subtotales, extrae TODOS
3. Si un campo puede interpretarse de múltiples formas, elige la más probable pero MARCA la incertidumbre
4. Captura las etiquetas originales junto con los valores
5. NO asumas que "Subtotal" siempre significa lo mismo

💡 CONFIANZA EN LA EXTRACCIÓN:
- Si estás 100% seguro del valor y su significado: Extrae normalmente
- Si el valor es claro pero el significado ambiguo: Extrae + nota en observaciones
- Si el valor es ilegible: Marca como null + nota en observaciones

🎯 EXTRACCIÓN COMPLETA - 4 SECCIONES:

1. ITEMS (productos/servicios):
   - Revisa CUIDADOSAMENTE cada FILA de la tabla
   - Cada FILA = UN item único (NO dupliques items)
   - Lee FILA POR FILA de izquierda a derecha:
     * Columna 1: código (corto, alfanumérico)
     * Columna 2: descripción (largo, texto descriptivo)
     * Columna 3: cantidad (número positivo)
     * Columna 4: unidad_medida (CJ, UN, KG, etc.)
     * Columna 5: precio_unitario (precio por UNA unidad)
     * Columna 6: subtotal (cantidad × precio_unitario)
   
   ⚠️⚠️⚠️ CRÍTICO - DIFERENCIA CÓDIGO vs CANTIDAD:
   - CÓDIGO: Aparece a la IZQUIERDA de la descripción, ANTES del texto
     Ejemplos: "48", "197", "2843", "84441", "100222"
     → Son identificadores, NO cantidades
     → Suelen tener muchos dígitos (4-6 dígitos)
   
   - CANTIDAD: Aparece a la DERECHA de la descripción, DESPUÉS del texto
     Ejemplos: "1", "2", "4", "6", "8"  
     → Son cantidades pedidas, valores PEQUEÑOS (típicamente 1-50)
     → Van seguidas de unidad de medida (CJ, UN, KG)
   
   🔍 PISTA CLAVE: La CANTIDAD multiplicada por PRECIO = SUBTOTAL
     Si código × precio = subtotal → ERROR, estás usando código como cantidad
     Si cantidad × precio ≈ subtotal → CORRECTO
   
   - NO pongas precios en 'descripcion' - solo texto descriptivo
   - NO pongas descripciones en 'codigo' - solo códigos cortos
   - Si un campo no está claro, déjalo vacío (null) - NO ADIVINES
   
   🆕 FACTURAS CON IMPUESTOS POR LÍNEA (opcional):
   Algunas facturas (ej: Coca-Cola, mayoristas) tienen impuestos desglosados POR ITEM:
     * descuento_item: Descuento aplicado a este item específico
     * subtotal_neto: Subtotal después de descuento (subtotal - descuento)
     * iva_tasa: Tasa de IVA aplicada (21, 10.5, 27, etc.)
     * iva_item: Monto de IVA calculado para este item
     * impuestos_internos_item: Impuestos internos para este item
     * subtotal_con_impuestos: Total final del item con todos los impuestos
   
   Si la factura tiene columnas como "DESCUENTO", "IVA 21%", "I.INTERNOS", "SUBTOTAL FINAL",
   EXTRAE estos valores para cada item. Esto permite validar mejor los totales.

2. PARTES (empresa y cliente):
   - EMPRESA (emisor de la factura):
     * razón_social (nombre completo de la empresa)
     * cuit (formato XX-XXXXXXXX-X, 11 dígitos)
     * condicion_iva (RESPONSABLE INSCRIPTO / MONOTRIBUTO / EXENTO / CONSUMIDOR FINAL)
     * domicilio_comercial, domicilio_calle, domicilio_localidad
     * provincia
     * ingresos_brutos (número de inscripción)
     * fecha_inicio_actividades (formato DD/MM/YYYY, si está disponible)
   
   - CLIENTE (receptor de la factura):
     * apellido_nombre_razon_social
     * cuit (formato XX-XXXXXXXX-X, puede ser null si es consumidor final)
     * condicion_iva
     * domicilio, domicilio_calle, domicilio_localidad
     * provincia

3. DOCUMENTO (datos del comprobante):
   - tipo_comprobante (FACTURA A / FACTURA B / FACTURA C / etc.)
   - codigo (código AFIP de 3 dígitos)
   - numero_comprobante (número completo del comprobante)
   - punto_venta (punto de venta, usualmente 4 dígitos)
   - fecha_emision (formato DD/MM/YYYY argentino)
   - cae (Código de Autorización Electrónico, 14 dígitos exactos)
   - fecha_vencimiento_cae (formato DD/MM/YYYY)
   - moneda (casi siempre "ARS" en Argentina)
   - condicion_venta (CONTADO / CUENTA CORRIENTE / etc.)

4. FISCALIDAD (totales e impuestos):
   - totales:
     * subtotal_gravado (suma de TODOS los items)
     * importe_total (total final a pagar)
     * descuentos (si hay)
   
   - impuestos:
     * iva: dict con tasas como claves y montos como valores
       Formato: {"21": monto, "105": monto, "27": monto}
     * percepcion_iva (si hay)
     * percepcion_ganancias (si hay)
     * percepcion_iibb: lista de dicts con provincia y monto
     * retencion_iva (si hay, puede ser None)
     * retencion_ganancias (si hay, puede ser None)
     * retencion_suss (si hay, puede ser None)
     * retenciones_iibb: lista de dicts con provincia y monto
     * impuestos_internos (si hay)
   
   - calculos:
     * items_count (cantidad de items)
     * items_subtotal_total (suma de subtotales de items)
     * diferencia_matematica (diferencia entre total calculado y declarado)

⚠️ ERRORES COMUNES A EVITAR:
- ❌ NO mezcles código con descripción
- ❌ NO dupliques items (cada fila es única)
- ❌ NO inventes datos - si no está claro, deja null
- ❌ NO pongas precios en descripción
- ❌ Verifica CADA multiplicación: cantidad × precio = subtotal
- ❌ Suma TODOS los items (no dejes ninguno fuera)
- ❌ NO confundas columnas al leer la tabla
- ❌ NO mezcles valores de diferentes filas

✅ EXTRAE CON EXTREMA PRECISIÓN en los cálculos matemáticos.
✅ Si un campo no es legible, déjalo vacío (null) - NUNCA inventes datos.
✅ Preserva el ORDEN de los items tal como aparecen en el documento.
✅ Verifica coherencia entre tipo de factura y condiciones IVA.
✅ Verifica que el CUIT tenga el formato correcto (11 dígitos con guiones).
✅ Verifica que el CAE tenga exactamente 14 dígitos.
"""


# =============================================================================
# GEMINI EXTRACTOR SERVICE
# =============================================================================

class GeminiExtractor:
    """
    Extractor completo usando Gemini 2.5 Flash.
    
    Realiza extracción completa de facturas argentinas sin necesidad de LlamaExtract.
    Compatible con la misma estructura de salida que LlamaExtract.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializar el extractor con credenciales de Google GenAI.
        
        Args:
            api_key: API key de Google AI (si no se provee, busca en env)
        """
        self.model_name = "gemini-2.5-flash"
        self.temperature = 0.0  # Determinístico para datos estructurados
        self.max_output_tokens = 49152  # 48K (balance entre capacidad y velocidad)
        self._uploaded_files_cache = {}
        
        # Usar autenticación centralizada
        self.client, self.auth_method = get_gemini_client(api_key)
        logger.info(f"✅ [GeminiExtractor] Cliente inicializado (método: {self.auth_method})")
    
    def _expand_refs(self, schema_dict, defs=None):
        """
        Expandir $ref inlines y remover $defs.
        
        Gemini no soporta $ref ni $defs, así que expandimos todas las referencias inline.
        """
        if defs is None and '$defs' in schema_dict:
            defs = schema_dict['$defs']
        
        if isinstance(schema_dict, dict):
            # Si hay un $ref, expandirlo
            if '$ref' in schema_dict and defs:
                ref_path = schema_dict['$ref']
                if ref_path.startswith('#/$defs/'):
                    def_name = ref_path.split('/')[-1]
                    if def_name in defs:
                        # Reemplazar la referencia con la definición expandida
                        expanded = defs[def_name].copy()
                        # Continuar expandiendo recursivamente
                        self._expand_refs(expanded, defs)
                        return expanded
            
            # Procesar recursivamente todos los valores
            for key, value in list(schema_dict.items()):
                if isinstance(value, dict):
                    expanded = self._expand_refs(value, defs)
                    if expanded is not value:
                        schema_dict[key] = expanded
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            expanded = self._expand_refs(item, defs)
                            if expanded is not item:
                                value[i] = expanded
        
        return schema_dict
    
    def _remove_additional_properties(self, schema_dict):
        """
        Remover recursivamente propiedades no soportadas por Gemini del schema JSON.
        
        Gemini no soporta:
        - additionalProperties
        - exclusiveMinimum
        - exclusiveMaximum
        - title
        - $defs (ya expandidas)
        - $ref (ya expandidas)
        """
        if isinstance(schema_dict, dict):
            # CASO ESPECIAL: si es un objeto con additionalProperties pero sin properties
            # (como Dict[str, float]), convertirlo a properties explícitas
            if (schema_dict.get('type') == 'object' and 
                'additionalProperties' in schema_dict and 
                ('properties' not in schema_dict or not schema_dict.get('properties'))):
                
                additional_props = schema_dict['additionalProperties']
                
                # Si es el campo "iva" (tasas de IVA), definir propiedades explícitas
                # Gemini necesita properties definidas, no puede tener objetos vacíos
                schema_dict['properties'] = {
                    "21": additional_props.copy() if isinstance(additional_props, dict) else {"type": "number"},
                    "105": additional_props.copy() if isinstance(additional_props, dict) else {"type": "number"},
                    "27": additional_props.copy() if isinstance(additional_props, dict) else {"type": "number"},
                    "5": additional_props.copy() if isinstance(additional_props, dict) else {"type": "number"},
                    "25": additional_props.copy() if isinstance(additional_props, dict) else {"type": "number"},
                }
            
            # Lista de propiedades a remover
            unsupported_props = [
                'additionalProperties',
                'exclusiveMinimum',
                'exclusiveMaximum',
                'title',
                '$defs',
                '$ref',
                'allOf',  # Gemini tampoco soporta allOf
            ]
            
            # Remover propiedades no soportadas
            for prop in unsupported_props:
                if prop in schema_dict:
                    del schema_dict[prop]
            
            # Procesar recursivamente todos los valores
            for key, value in schema_dict.items():
                if isinstance(value, dict):
                    self._remove_additional_properties(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._remove_additional_properties(item)
    
    def _upload_file_with_cache(self, file_path: str):
        """Subir archivo con cache por hash de contenido - Soporta PDF e imágenes"""
        # Calcular hash del archivo
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = hashlib.md5(content).hexdigest()
        
        # Verificar cache
        if file_hash in self._uploaded_files_cache:
            logger.debug(f"📋 [GeminiExtractor] Usando archivo cached: {file_hash[:8]}...")
            return self._uploaded_files_cache[file_hash]
        
        # Determinar tipo de archivo
        file_path_obj = pathlib.Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        # Verificar que el archivo sea compatible
        supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
        if file_ext not in supported_extensions:
            raise ValueError(f"Tipo de archivo no soportado: {file_ext}. Soportados: {supported_extensions}")
        
        logger.info(f"📤 [GeminiExtractor] Subiendo {file_ext.upper()} con File API: {file_path_obj.name}")
        
        # Subir archivo (File API soporta tanto PDF como imágenes)
        uploaded_file = self.client.files.upload(file=file_path_obj)
        
        # Guardar en cache
        self._uploaded_files_cache[file_hash] = uploaded_file
        logger.info(f"✅ [GeminiExtractor] Archivo subido y cached: {file_hash[:8]}... ({file_ext.upper()})")
        
        return uploaded_file
    
    def _get_schema(self, schema_type: str = 'completo', segments: Optional[List[str]] = None) -> Type[BaseModel]:
        """
        Obtener el schema Pydantic apropiado.
        
        Args:
            schema_type: 'completo', 'simplificado', o 'modular'
            segments: Lista de segmentos si schema_type='modular'
        
        Returns:
            Clase Pydantic schema
        """
        if schema_type == "simplificado":
            return InvoiceSimplificado
        elif schema_type == "modular":
            schema_composer = SchemaComposer(segments=segments)
            return schema_composer.get_schema()
        else:
            return InvoiceComplete
    
    def _build_extraction_prompt(
        self, 
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Construir prompt optimizado para extracción completa.
        
        Args:
            schema_type: Tipo de schema
            segments: Segmentos específicos a extraer
            additional_context: Contexto adicional para enriquecer el prompt (🆕)
        
        Returns:
            Prompt optimizado
        """
        base_prompt = ""
        
        if schema_type == "modular" and segments:
            segments_str = ", ".join(segments)
            base_prompt = f"""
📋 INSTRUCCIONES DE EXTRACCIÓN MODULAR

Extrae SOLAMENTE las siguientes secciones de este comprobante argentino:
{segments_str}

{'- ITEMS: Todos los productos/servicios de la tabla' if 'items' in segments else ''}
{'- PARTES: Datos de empresa (emisor) y cliente (receptor)' if 'partes' in segments else ''}
{'- DOCUMENTO: Tipo, número, CAE, fechas del comprobante' if 'documento' in segments else ''}
{'- FISCALIDAD: Totales, IVA, percepciones, retenciones' if 'fiscalidad' in segments else ''}

⚠️ IMPORTANTE: Extrae SOLO lo solicitado. Los demás campos déjalos vacíos o null.

✅ Mantén la MÁXIMA PRECISIÓN en cálculos matemáticos.
✅ Si un dato no está claro, devuelve null - NO inventes.
"""
        else:
            base_prompt = """
📋 INSTRUCCIONES DE EXTRACCIÓN COMPLETA

Extrae TODAS las secciones de este comprobante argentino:

1. ✅ ITEMS: Todos los productos/servicios de la tabla
2. ✅ PARTES: Datos completos de empresa y cliente
3. ✅ DOCUMENTO: Tipo, número, CAE, fechas
4. ✅ FISCALIDAD: Totales, impuestos discriminados, percepciones, retenciones

⚠️ PRECISIÓN MATEMÁTICA ES CRÍTICA:
- Verifica que cada item: cantidad × precio = subtotal
- Verifica que suma de items = subtotal_gravado
- Verifica que subtotal + IVA + percepciones = importe_total

✅ Extrae con MÁXIMA PRECISIÓN.
✅ Si un dato no está claro, devuelve null - NO inventes.
✅ Preserva el orden de los items tal como aparecen.
"""
        
        # 🆕 Agregar contexto adicional si se provee
        if additional_context:
            base_prompt += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            base_prompt += f"📌 CONTEXTO ADICIONAL IMPORTANTE:\n\n"
            base_prompt += additional_context
            base_prompt += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            base_prompt += "\n⚠️ USA ESTE CONTEXTO para validar la consistencia de tu extracción."
        
        return base_prompt
    
    def extract_invoice_data(
        self,
        image_path: str,
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None,
        additional_context: Optional[str] = None,
        use_multi_image: bool = False,  # 🔧 Deshabilitado - empeora resultados
        use_smart_crops: bool = False   # 🆕 Usa recortes inteligentes por región
    ) -> Dict[str, Any]:
        """
        Alias para extract_complete (para compatibilidad con orchestrator).
        
        Args:
            image_path: Ruta a la imagen de factura
            schema_type: 'completo', 'simplificado', o 'modular'
            segments: Lista de segmentos si schema_type='modular'
            additional_context: Contexto adicional para enriquecer el prompt
            use_multi_image: Si True, envía múltiples versiones de la imagen (zoom, contraste)
            use_smart_crops: Si True, envía recortes por región (header, items, footer)
        """
        return self.extract_complete(
            image_path, schema_type, segments, additional_context, 
            use_multi_image, use_smart_crops
        )
    
    def extract_complete(
        self, 
        file_path: str,
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None,
        additional_context: Optional[str] = None,
        use_multi_image: bool = False,  # 🔧 Deshabilitado - empeora resultados
        use_smart_crops: bool = False   # 🆕 Usa recortes inteligentes por región
    ) -> Dict[str, Any]:
        """
        Realizar extracción completa con Gemini 2.5 Flash.
        
        Args:
            file_path: Ruta al documento (imagen o PDF)
            schema_type: 'completo', 'simplificado', o 'modular'
            segments: Lista de segmentos si schema_type='modular'
            additional_context: Contexto adicional para enriquecer el prompt
            use_multi_image: Si True, envía múltiples versiones de la imagen (zoom, contraste)
            use_smart_crops: Si True, envía recortes por región (header, items, footer) - RECOMENDADO
        
        Returns:
            {
                'success': True/False,
                'data': {...},  # Estructura idéntica a LlamaExtract
                'metadata': {
                    'extraction_time': float,
                    'schema_type': str,
                    'extractor': 'gemini-2.5-flash',
                    'file_name': str,
                    'multi_image_used': bool,
                    'smart_crops_used': bool
                },
                'error': str  # Solo si success=False
            }
        """
        start_time = datetime.now()
        image_processor = None
        
        try:
            logger.info("=" * 80)
            logger.info("🤖 [GeminiExtractor] INICIANDO EXTRACCIÓN COMPLETA CON GEMINI 2.5 FLASH")
            logger.info(f"   Archivo: {file_path}")
            logger.info(f"   Schema: {schema_type}")
            
            # Determinar modo de imagen
            is_image_file = file_path.lower().endswith(('.jpg', '.jpeg', '.png'))
            should_use_smart_crops = use_smart_crops and VISION_AVAILABLE and is_image_file
            should_use_multi_image = use_multi_image and VISION_AVAILABLE and is_image_file and not should_use_smart_crops
            
            if should_use_smart_crops:
                logger.info(f"   Modo imagen: 🎯 Smart Crops (recortes por región)")
            elif should_use_multi_image:
                logger.info(f"   Modo imagen: 🖼️ Multi-imagen (zoom, contraste)")
            else:
                logger.info(f"   Modo imagen: 📄 Normal (imagen única)")
            
            if segments:
                logger.info(f"   Segmentos: {segments}")
            logger.info("=" * 80)
            
            # 1. Subir archivo(s) a Gemini File API
            uploaded_files = []
            image_variants = []
            region_crops = []
            smart_cropper = None
            
            if should_use_smart_crops:
                # 🎯 MODO SMART CROPS: Recortes inteligentes por región
                logger.info("🎯 Generando recortes inteligentes por región...")
                smart_cropper = SmartCropper()
                region_crops = smart_cropper.create_region_crops(
                    file_path,
                    regions=['header', 'items', 'footer'],
                    enhance=True,
                    zoom_factor=1.5
                )
                
                # Subir todos los crops
                for crop in region_crops:
                    uploaded = self._upload_file_with_cache(crop.path)
                    uploaded_files.append(uploaded)
                    logger.info(f"   📤 {crop.region_name.upper()}: {uploaded.name}")
                    
            elif should_use_multi_image:
                # 🖼️ MODO MULTI-IMAGEN: Variantes de zoom/contraste
                logger.info("🖼️ Generando variantes de imagen para mejor extracción...")
                image_processor = MultiImageProcessor()
                image_variants = image_processor.create_variants(
                    file_path,
                    include_original=True,
                    include_zoomed=True,
                    include_enhanced=True,
                    zoom_factor=2.0,
                    contrast_factor=1.4
                )
                
                # Subir todas las variantes
                for variant in image_variants:
                    uploaded = self._upload_file_with_cache(variant.path)
                    uploaded_files.append(uploaded)
                    logger.info(f"   📤 {variant.description}: {uploaded.name}")
            else:
                # 📄 MODO NORMAL: Solo imagen original
                uploaded_file = self._upload_file_with_cache(file_path)
                uploaded_files.append(uploaded_file)
                logger.info(f"📤 Archivo subido: {uploaded_file.name}")
            
            # 2. Obtener schema apropiado
            schema_class = self._get_schema(schema_type, segments)
            logger.info(f"📋 Schema seleccionado: {schema_class.__name__}")
            
            # 3. Construir prompt (con instrucciones según modo de imagen)
            extraction_prompt = self._build_extraction_prompt(schema_type, segments, additional_context)
            
            if should_use_smart_crops and region_crops:
                # Añadir instrucciones específicas por región
                extraction_prompt = build_regional_prompt(region_crops, extraction_prompt)
                logger.info(f"📝 Prompt generado con instrucciones por REGIÓN ({len(extraction_prompt)} chars)")
            elif should_use_multi_image and image_variants:
                extraction_prompt = build_multi_image_prompt(image_variants, extraction_prompt)
                logger.info(f"📝 Prompt generado con instrucciones multi-imagen ({len(extraction_prompt)} chars)")
            else:
                logger.info(f"📝 Prompt generado ({len(extraction_prompt)} chars)")
            
            if additional_context:
                logger.info(f"   🆕 Con contexto adicional: {len(additional_context)} chars")
            
            # 4. Configurar generación con schema estructurado
            # Construir contents intercalando imágenes con el prompt
            contents = []
            for uploaded_file in uploaded_files:
                contents.append(uploaded_file)
            contents.append(extraction_prompt)
            
            # Convertir schema Pydantic a dict JSON Schema compatible con Gemini
            # 1. Generar JSON Schema
            json_schema = schema_class.model_json_schema()
            # 2. Expandir todas las $ref inline (Gemini no soporta $ref ni $defs)
            json_schema = self._expand_refs(json_schema)
            # 3. Remover propiedades no soportadas por Gemini
            self._remove_additional_properties(json_schema)
            
            config = {
                "system_instruction": SYSTEM_INSTRUCTION_CONTADOR_COMPLETO,
                "response_mime_type": "application/json",
                "response_schema": json_schema,  # 🎯 Schema JSON (sin additionalProperties)
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            }
            
            logger.info("🚀 Llamando a Gemini 2.5 Flash con schema estructurado...")
            
            # 5. Generar contenido (con retry automático para 429 errors)
            response = retry_with_exponential_backoff(
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                ),
                max_retries=5,
                initial_delay=2.0
            )
            
            # 6. Parsear respuesta
            logger.info("🔍 Analizando respuesta de Gemini...")
            
            if hasattr(response, 'parsed') and response.parsed:
                result_obj = response.parsed
                logger.info("✅ Gemini devolvió respuesta estructurada (response.parsed)")
            else:
                # FALLBACK - Parsear JSON manualmente
                logger.warning("⚠️ response.parsed no disponible, parseando JSON manualmente")
                
                # Extraer texto de la respuesta
                if not hasattr(response, 'text') or response.text is None:
                    logger.error("❌ response.text es None o no existe")
                    
                    # Intentar obtener de candidates
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if (hasattr(candidate, 'content') and 
                            hasattr(candidate.content, 'parts') and 
                            candidate.content.parts is not None and
                            len(candidate.content.parts) > 0):
                            text = candidate.content.parts[0].text
                            logger.info(f"✅ Texto extraído de candidates")
                        else:
                            # Gemini bloqueó la respuesta o no devolvió contenido
                            logger.error("❌ Gemini no devolvió contenido válido")
                            logger.error(f"   Candidate: {candidate}")
                            
                            # ✅ Mejor manejo de finish_reason
                            if hasattr(candidate, 'finish_reason'):
                                finish_reason = str(candidate.finish_reason)
                                logger.error(f"   Finish reason: {finish_reason}")
                                
                                if 'MAX_TOKENS' in finish_reason:
                                    raise Exception(
                                        f"Gemini agotó tokens de salida (MAX_TOKENS). "
                                        f"La respuesta es muy larga para max_output_tokens={self.max_output_tokens}. "
                                        f"La factura es muy compleja. Considera usar extracción modular por secciones."
                                    )
                                elif 'SAFETY' in finish_reason:
                                    raise Exception("Gemini bloqueó respuesta por motivos de seguridad (safety)")
                                else:
                                    raise Exception(f"Gemini finalizó inesperadamente: {finish_reason}")
                            
                            raise Exception("Gemini no devolvió contenido (posiblemente bloqueado por safety)")
                    else:
                        raise Exception("No hay respuesta válida de Gemini")
                else:
                    text = response.text.strip()
                
                # Parsear JSON
                try:
                    response_data = json.loads(text)
                    result_obj = schema_class(**response_data)
                    logger.info("✅ JSON parseado manualmente - ÉXITO")
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.error(f"❌ Gemini devolvió JSON inválido: {e}")
                    logger.error(f"Texto recibido: {text[:500]}...")
                    raise Exception(f"Error parseando respuesta de Gemini: {e}")
            
            # 7. Convertir Pydantic a dict (formato compatible con LlamaExtract)
            if hasattr(result_obj, 'model_dump'):
                extracted_data = result_obj.model_dump()
            elif hasattr(result_obj, 'dict'):
                extracted_data = result_obj.dict()
            else:
                extracted_data = dict(result_obj)
            
            extraction_time = (datetime.now() - start_time).total_seconds()
            
            # 8. Construir metadata (compatible con LlamaExtract)
            metadata = {
                'extraction_time': extraction_time,
                'schema_type': schema_type,
                'extractor': 'gemini-2.5-flash',
                'file_name': pathlib.Path(file_path).name,
                'multi_image_used': should_use_multi_image,
                'smart_crops_used': should_use_smart_crops,  # 🆕
                'image_variants_count': len(image_variants) if should_use_multi_image else (len(region_crops) if should_use_smart_crops else 1)
            }
            
            if schema_type == "modular" and segments:
                metadata['segments'] = segments
            
            if should_use_smart_crops:
                metadata['regions_processed'] = [crop.region_name for crop in region_crops]
            
            logger.info(f"✅ Extracción completada en {extraction_time:.2f}s")
            if should_use_smart_crops:
                logger.info(f"   🎯 Usó {len(region_crops)} recortes por región")
            elif should_use_multi_image:
                logger.info(f"   🖼️ Usó {len(image_variants)} variantes de imagen")
            logger.info("=" * 80)
            logger.info("🎉 EXTRACCIÓN COMPLETA EXITOSA")
            logger.info("=" * 80)
            
            # 🆕 Limpiar archivos temporales
            if smart_cropper:
                smart_cropper.cleanup()
            if image_processor:
                image_processor.cleanup()
            
            return {
                'success': True,
                'data': extracted_data,
                'metadata': metadata
            }
            
        except Exception as e:
            extraction_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error en extracción con Gemini: {str(e)}", exc_info=True)
            
            # Limpiar archivos temporales incluso en error
            if smart_cropper:
                smart_cropper.cleanup()
            if image_processor:
                image_processor.cleanup()
            
            return {
                'success': False,
                'error': str(e),
                'metadata': {
                    'extraction_time': extraction_time,
                    'schema_type': schema_type,
                    'extractor': 'gemini-2.5-flash',
                    'file_name': pathlib.Path(file_path).name if file_path else None
                }
            }
    
    def retry_with_context(
        self,
        file_path: str,
        original_data: Dict[str, Any],
        validation_result: Dict[str, Any],
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Re-intentar extracción con contexto de errores.
        
        Similar a GeminiCorrector.retry_extraction_with_gemini() pero con schema completo.
        
        Args:
            file_path: Ruta al documento
            original_data: Datos de la primera extracción
            validation_result: Errores detectados por validadores
            schema_type: Tipo de schema
            segments: Segmentos específicos
        
        Returns:
            Nuevos datos extraídos o None si falla
        """
        try:
            logger.info("=" * 80)
            logger.info("🔄 [GeminiExtractor] RE-EXTRACCIÓN CON CONTEXTO DE ERRORES")
            logger.info("=" * 80)
            
            # 1. Subir archivo
            uploaded_file = self._upload_file_with_cache(file_path)
            
            # 2. Construir prompt con contexto de errores
            retry_prompt = self._build_retry_prompt(original_data, validation_result)
            logger.info(f"📝 Prompt de retry generado ({len(retry_prompt)} chars)")
            
            # 3. Obtener schema
            schema_class = self._get_schema(schema_type, segments)
            
            # 4. Configurar generación
            contents = [uploaded_file, retry_prompt]
            
            # Convertir schema a JSON Schema compatible con Gemini
            json_schema = schema_class.model_json_schema()
            json_schema = self._expand_refs(json_schema)
            self._remove_additional_properties(json_schema)
            
            config = {
                "system_instruction": SYSTEM_INSTRUCTION_CONTADOR_COMPLETO,
                "response_mime_type": "application/json",
                "response_schema": json_schema,
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            }
            
            logger.info("🚀 Llamando a Gemini con contexto de errores...")
            
            # 5. Generar contenido (con retry automático para 429 errors)
            response = retry_with_exponential_backoff(
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                ),
                max_retries=5,
                initial_delay=2.0
            )
            
            # 6. Parsear respuesta (mismo código que extract_complete)
            if hasattr(response, 'parsed') and response.parsed:
                result_obj = response.parsed
            else:
                if hasattr(response, 'text') and response.text:
                    text = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    text = response.candidates[0].content.parts[0].text
                else:
                    return None
                
                response_data = json.loads(text)
                result_obj = schema_class(**response_data)
            
            # 7. Convertir a dict
            if hasattr(result_obj, 'model_dump'):
                extracted_data = result_obj.model_dump()
            elif hasattr(result_obj, 'dict'):
                extracted_data = result_obj.dict()
            else:
                extracted_data = dict(result_obj)
            
            logger.info("✅ Re-extracción con contexto completada")
            logger.info("=" * 80)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ Error en retry con contexto: {str(e)}", exc_info=True)
            return None
    
    def _build_retry_prompt(
        self,
        original_data: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> str:
        """
        Construir prompt enriquecido con contexto de errores.
        
        Args:
            original_data: Datos de primera extracción
            validation_result: Errores detectados
        
        Returns:
            Prompt con contexto de errores
        """
        errors = validation_result.get("errors", []) or validation_result.get("validation_errors", [])
        
        prompt_parts = [
            "🚨 ATENCIÓN: La extracción anterior tuvo ERRORES.",
            "",
            "📋 ERRORES DETECTADOS EN LA PRIMERA EXTRACCIÓN:",
        ]
        
        for i, error in enumerate(errors[:10], 1):  # Max 10 errores
            prompt_parts.append(f"  {i}. {error}")
        
        # Contexto de primera extracción
        prompt_parts.extend([
            "",
            "📊 DATOS EXTRAÍDOS EN PRIMERA EXTRACCIÓN (CON ERRORES):",
            "",
        ])
        
        # Mostrar items si hay
        if "items" in original_data:
            items = original_data["items"]
            prompt_parts.append(f"Items extraídos ({len(items)} items):")
            for i, item in enumerate(items[:5], 1):
                codigo = item.get('codigo', 'N/A')
                desc = item.get('descripcion', 'N/A')[:30]
                cant = item.get('cantidad', 0)
                precio = item.get('precio_unitario', 0)
                subtotal = item.get('subtotal', 0)
                esperado = cant * precio
                ok = "✅" if abs(esperado - subtotal) < 0.01 else "❌"
                prompt_parts.append(
                    f"  {i}. {ok} {codigo} | {desc}... | {cant} × ${precio:,.2f} = ${subtotal:,.2f}"
                )
            if len(items) > 5:
                prompt_parts.append(f"  ... y {len(items) - 5} items más")
        
        # Mostrar totales si hay
        if "fiscalidad" in original_data:
            fiscalidad = original_data["fiscalidad"]
            totales = fiscalidad.get("totales", {})
            prompt_parts.extend([
                "",
                "Totales extraídos:",
                f"  - Subtotal gravado: ${totales.get('subtotal_gravado', 0):,.2f}",
                f"  - Importe total: ${totales.get('importe_total', 0):,.2f}",
            ])
        
        prompt_parts.extend([
            "",
            "=" * 60,
            "📸 NUEVA EXTRACCIÓN - CORRIGE LOS ERRORES:",
            "=" * 60,
            "",
            "🎯 TU TAREA: Re-extraer CORRECTAMENTE, corrigiendo los errores anteriores.",
            "",
            "🔍 INSTRUCCIONES CRÍTICAS:",
            "1. Lee CUIDADOSAMENTE el documento original",
            "2. Verifica TODOS los cálculos matemáticos",
            "3. NO copies los datos anteriores - EXTRAE DE NUEVO del documento",
            "4. Corrige específicamente los errores listados arriba",
            "5. Si un dato no está claro, devuelve null - NO ADIVINES",
            "",
            "✅ EXTRAE con EXTREMA PRECISIÓN.",
            ""
        ])
        
        return "\n".join(prompt_parts)

