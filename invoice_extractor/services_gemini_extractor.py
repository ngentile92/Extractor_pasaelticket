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
3. Schema completo (ComprobanteArgentino)
4. Prompt optimizado para extracción completa

Y devuelve estructura idéntica a LlamaExtract para compatibilidad total.
"""

import os
import json
import logging
import pathlib
import hashlib
import tempfile
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
from google import genai
from pydantic import BaseModel

# Importar schemas del sistema
from invoice_extractor.schemas import (
    ComprobanteArgentino,
    ComprobanteSimplificado,
    SchemaComposer
)

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM INSTRUCTIONS PARA GEMINI
# =============================================================================

SYSTEM_INSTRUCTION_CONTADOR_COMPLETO = """
Eres un contador público argentino certificado con 25+ años de experiencia especializado en:

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

🔧 CORRECCIÓN OCR:
- Corrige errores típicos de OCR:
  * ø → é (común en "José", "León")
  * rn → m (común en "monto")
  * 0 → O (cero vs letra O)
  * 6 → G (seis vs G)
  * S → 5 (S vs cinco)
  * l → I (ele minúscula vs i mayúscula)
- CUIT: SIEMPRE formato XX-XXXXXXXX-X (11 dígitos con guiones)
- Números: 
  * Miles: separados con punto (1.234,56)
  * Decimales: coma (no punto)
  * Ejemplo: $187.276,70

⚖️ PRECISIÓN MATEMÁTICA CRÍTICA:
- CADA item: cantidad × precio_unitario = subtotal (verificar con 2 decimales)
- SUMA items: Σ(subtotal de todos los items) = subtotal_gravado
- TOTAL FINAL: subtotal_gravado + IVA + percepciones - retenciones - descuentos = importe_total
- SI HAY ERROR MATEMÁTICO: revisa TODOS los números hasta que cuadre
- Tolerancia: máximo 0.01 de diferencia por redondeo

🎯 EXTRACCIÓN COMPLETA - 4 SECCIONES:

1. ITEMS (productos/servicios):
   - Revisa CUIDADOSAMENTE cada FILA de la tabla
   - Cada FILA = UN item único (NO dupliques items)
   - Lee COLUMNA POR COLUMNA de izquierda a derecha:
     * Columna 1: código (corto, ej: "100972", "48", "2843")
     * Columna 2: descripción (largo, ej: "MONSTER GREEN EAN 473X6")
     * Columna 3: cantidad (número positivo)
     * Columna 4: unidad_medida (ej: "CJ", "UN", "KG")
     * Columna 5: precio_unitario (precio por UNA unidad)
     * Columna 6: subtotal (cantidad × precio_unitario)
   - NO pongas precios en 'descripcion' - solo texto descriptivo
   - NO pongas descripciones en 'codigo' - solo códigos cortos
   - Si un campo no está claro, déjalo vacío (null) - NO ADIVINES

2. PARTES (empresa y cliente):
   - EMPRESA (emisor de la factura):
     * razón_social (nombre completo de la empresa)
     * cuit (formato XX-XXXXXXXX-X)
     * condicion_iva (ej: "RESPONSABLE INSCRIPTO")
     * domicilio_comercial, domicilio_calle, domicilio_localidad
     * provincia
     * ingresos_brutos (número de inscripción)
     * fecha_inicio_actividades (si está disponible)
   
   - CLIENTE (receptor de la factura):
     * apellido_nombre_razon_social
     * cuit (formato XX-XXXXXXXX-X, puede ser null si es consumidor final)
     * condicion_iva
     * domicilio, domicilio_calle, domicilio_localidad
     * provincia

3. DOCUMENTO (datos del comprobante):
   - tipo_comprobante (ej: "FACTURA A", "FACTURA B")
   - codigo (ej: "001", "006", "011")
   - numero_comprobante (número completo del comprobante)
   - punto_venta (punto de venta, usualmente 4 dígitos)
   - fecha_emision (formato DD/MM/YYYY argentino)
   - cae (Código de Autorización Electrónico, 14 dígitos)
   - fecha_vencimiento_cae (formato DD/MM/YYYY)
   - moneda (casi siempre "ARS" en Argentina)
   - condicion_venta (ej: "CONTADO", "CUENTA CORRIENTE")

4. FISCALIDAD (totales e impuestos):
   - totales:
     * subtotal_gravado (suma de TODOS los items)
     * importe_total (total final a pagar)
     * descuentos (si hay)
   
   - impuestos:
     * iva: {"21": monto_iva_21, "105": monto_iva_105, ...}
       Ejemplo: {"21": 187276.7, "105": 0}
     * percepcion_iva (si hay)
     * percepcion_ganancias (si hay)
     * percepcion_iibb: [{"provincia": "CABA", "monto": 1000}] (si hay)
     * retencion_iva (si hay, puede ser None)
     * retencion_ganancias (si hay, puede ser None)
     * retencion_suss (si hay, puede ser None)
     * retenciones_iibb: [] (si hay)
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

✅ EXTRAE CON EXTREMA PRECISIÓN en los cálculos matemáticos.
✅ Si un campo no es legible, déjalo vacío (null) - NUNCA inventes datos.
✅ Preserva el ORDEN de los items tal como aparecen en el documento.
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
    
    def __init__(self, api_key: Optional[str] = None, service_account_path: Optional[str] = None):
        """
        Inicializar el extractor con credenciales de Google GenAI.
        
        Args:
            api_key: API key de Google AI (si no se provee, busca en env)
            service_account_path: Path a service account JSON (alternativa a API key)
        """
        self.model_name = "gemini-2.5-flash"
        self.temperature = 0.0  # Determinístico para datos estructurados
        self.max_output_tokens = 16384
        self._uploaded_files_cache = {}
        
        self._init_genai_client(api_key, service_account_path)
    
    def _init_genai_client(self, api_key: Optional[str], service_account_path: Optional[str]):
        """Inicializar cliente Google GenAI con soporte para Railway/production"""
        try:
            # Opción 1: API Key desde variable de entorno (buscar ambas variantes)
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
            
            if api_key:
                logger.info(f"🔐 [GeminiExtractor] Usando Google API Key: {api_key[:10]}...")
                self.client = genai.Client(api_key=api_key)
                self.auth_method = "api_key"
                logger.info("✅ [GeminiExtractor] GenAI Client inicializado con API Key")
                return
            
            # Opción 2: Service Account desde JSON string (Railway/production)
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_json:
                logger.info("🔐 [GeminiExtractor] Usando Service Account desde variable de entorno JSON")
                # Crear archivo temporal con las credenciales
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    temp_file.write(service_account_json)
                    temp_path = temp_file.name
                
                # Configurar GOOGLE_APPLICATION_CREDENTIALS temporalmente
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
                self.client = genai.Client()
                self.auth_method = "service_account_json"
                logger.info("✅ [GeminiExtractor] GenAI Client inicializado con Service Account (JSON env var)")
                return
            
            # Opción 3: Application Default Credentials (archivo o ADC)
            logger.info("🔐 [GeminiExtractor] Intentando Application Default Credentials...")
            self.client = genai.Client()
            self.auth_method = "adc"
            logger.info("✅ [GeminiExtractor] GenAI Client inicializado con ADC")
                
        except Exception as e:
            logger.error(f"❌ [GeminiExtractor] Error inicializando GenAI Client: {e}")
            logger.error("💡 Configura GOOGLE_API_KEY o GOOGLE_SERVICE_ACCOUNT_JSON en .env")
            raise
    
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
            return ComprobanteSimplificado
        elif schema_type == "modular":
            schema_composer = SchemaComposer(segments=segments)
            return schema_composer.get_schema()
        else:
            return ComprobanteArgentino
    
    def _build_extraction_prompt(
        self, 
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None
    ) -> str:
        """
        Construir prompt optimizado para extracción completa.
        
        Args:
            schema_type: Tipo de schema
            segments: Segmentos específicos a extraer
        
        Returns:
            Prompt optimizado
        """
        if schema_type == "modular" and segments:
            segments_str = ", ".join(segments)
            return f"""
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
            return """
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
    
    def extract_complete(
        self, 
        file_path: str,
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Realizar extracción completa con Gemini 2.5 Flash.
        
        Args:
            file_path: Ruta al documento (imagen o PDF)
            schema_type: 'completo', 'simplificado', o 'modular'
            segments: Lista de segmentos si schema_type='modular'
        
        Returns:
            {
                'success': True/False,
                'data': {...},  # Estructura idéntica a LlamaExtract
                'metadata': {
                    'extraction_time': float,
                    'schema_type': str,
                    'extractor': 'gemini-2.5-flash',
                    'file_name': str
                },
                'error': str  # Solo si success=False
            }
        """
        start_time = datetime.now()
        
        try:
            logger.info("=" * 80)
            logger.info("🤖 [GeminiExtractor] INICIANDO EXTRACCIÓN COMPLETA CON GEMINI 2.5 FLASH")
            logger.info(f"   Archivo: {file_path}")
            logger.info(f"   Schema: {schema_type}")
            if segments:
                logger.info(f"   Segmentos: {segments}")
            logger.info("=" * 80)
            
            # 1. Subir archivo a Gemini File API
            uploaded_file = self._upload_file_with_cache(file_path)
            logger.info(f"📤 Archivo subido: {uploaded_file.name}")
            
            # 2. Obtener schema apropiado
            schema_class = self._get_schema(schema_type, segments)
            logger.info(f"📋 Schema seleccionado: {schema_class.__name__}")
            
            # 3. Construir prompt
            extraction_prompt = self._build_extraction_prompt(schema_type, segments)
            logger.info(f"📝 Prompt generado ({len(extraction_prompt)} chars)")
            
            # 4. Configurar generación con schema estructurado
            contents = [
                uploaded_file,
                extraction_prompt
            ]
            
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
            
            # 5. Generar contenido
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
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
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            text = candidate.content.parts[0].text
                            logger.info(f"✅ Texto extraído de candidates")
                        else:
                            raise Exception("No se pudo extraer texto de la respuesta de Gemini")
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
                'file_name': pathlib.Path(file_path).name
            }
            
            if schema_type == "modular" and segments:
                metadata['segments'] = segments
            
            logger.info(f"✅ Extracción completada en {extraction_time:.2f}s")
            logger.info("=" * 80)
            logger.info("🎉 EXTRACCIÓN COMPLETA EXITOSA")
            logger.info("=" * 80)
            
            return {
                'success': True,
                'data': extracted_data,
                'metadata': metadata
            }
            
        except Exception as e:
            extraction_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error en extracción con Gemini: {str(e)}", exc_info=True)
            
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
            
            # 5. Generar contenido
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
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

