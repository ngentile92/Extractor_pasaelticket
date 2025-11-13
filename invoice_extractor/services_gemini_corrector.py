"""
🤖 Gemini Corrector Service - Re-extracción inteligente con Gemini 2.5 Flash

Este servicio utiliza Google Gemini 2.5 Flash para re-intentar la extracción de datos
cuando se detectan errores matemáticos o de validación en la primera extracción.

Gemini recibe:
1. El documento original (imagen/PDF)
2. Los datos extraídos originalmente por LlamaExtract
3. Los errores matemáticos detectados por el validator
4. Contexto específico sobre qué corregir

Y devuelve una nueva extracción más precisa.
"""

import os
import json
import logging
import pathlib
import hashlib
from typing import Dict, Any, Optional, List
from google import genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMAS PYDANTIC PARA GEMINI
# =============================================================================

class GeminiInvoiceItem(BaseModel):
    """Item individual de la factura - Schema optimizado para Gemini"""
    codigo: Optional[str] = Field(None, description="Código del producto (corto, alfanumérico)")
    descripcion: str = Field(..., description="Descripción del producto/servicio")
    cantidad: float = Field(..., description="Cantidad (debe ser > 0)")
    unidad_medida: Optional[str] = Field(None, description="Unidad: UN, KG, LT, CJ, etc.")
    precio_unitario: float = Field(..., description="Precio por unidad (debe ser >= 0)")
    subtotal: float = Field(..., description="cantidad × precio_unitario (debe ser >= 0)")


class GeminiInvoiceFiscalidad(BaseModel):
    """Datos fiscales e impositivos - Schema optimizado para Gemini"""
    subtotal_gravado: float = Field(..., description="Subtotal antes de impuestos (debe ser >= 0)")
    iva_21: float = Field(default=0.0, description="IVA 21% (debe ser >= 0)")
    iva_105: float = Field(default=0.0, description="IVA 10.5% (debe ser >= 0)")
    iva_27: float = Field(default=0.0, description="IVA 27% (debe ser >= 0)")
    percepcion_iibb: float = Field(default=0.0, description="Percepción IIBB (debe ser >= 0)")
    impuestos_internos: float = Field(default=0.0, description="Impuestos internos (debe ser >= 0)")
    importe_total: float = Field(..., description="Total final a pagar (debe ser >= 0)")


class GeminiInvoiceComplete(BaseModel):
    """Schema completo para re-extracción con Gemini - Solo items + fiscalidad"""
    items: List[GeminiInvoiceItem] = Field(..., description="Items de la factura")
    fiscalidad: GeminiInvoiceFiscalidad = Field(..., description="Datos fiscales")


# =============================================================================
# GEMINI CORRECTOR SERVICE
# =============================================================================

class GeminiCorrector:
    """
    Corrector inteligente que usa Gemini 2.5 Flash para re-extraer datos con contexto de errores.
    """
    
    def __init__(self, api_key: Optional[str] = None, service_account_path: Optional[str] = None):
        """
        Inicializar el corrector con credenciales de Google GenAI.
        
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
        import tempfile
        
        try:
            # Opción 1: API Key desde variable de entorno (buscar ambas variantes)
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
            
            if api_key:
                logger.info(f"🔐 Usando Google API Key: {api_key[:10]}...")
                self.client = genai.Client(api_key=api_key)
                self.auth_method = "api_key"
                logger.info("✅ GenAI Client inicializado con API Key")
                return
            
            # Opción 2: Service Account desde JSON string (Railway/production)
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_json:
                logger.info("🔐 Usando Service Account desde variable de entorno JSON")
                # Crear archivo temporal con las credenciales
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    temp_file.write(service_account_json)
                    temp_path = temp_file.name
                
                # Configurar GOOGLE_APPLICATION_CREDENTIALS temporalmente
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
                self.client = genai.Client()
                self.auth_method = "service_account_json"
                logger.info("✅ GenAI Client inicializado con Service Account (JSON env var)")
                return
            
            # Opción 3: Application Default Credentials (archivo o ADC)
            # Esto usa automáticamente GOOGLE_APPLICATION_CREDENTIALS si está configurado
            logger.info("🔐 Intentando Application Default Credentials...")
            self.client = genai.Client()
            self.auth_method = "adc"
            logger.info("✅ GenAI Client inicializado con ADC")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando GenAI Client: {e}")
            logger.error("💡 Configura GOOGLE_API_KEY o GOOGLE_SERVICE_ACCOUNT_JSON en .env")
            raise
    
    def _upload_file_with_cache(self, file_path: str):
        """Subir archivo con cache por hash de contenido - Soporta PDF e imágenes"""
        # Calcular hash del archivo
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = hashlib.md5(content).hexdigest()
        
        # Verificar cache
        if file_hash in self._uploaded_files_cache:
            logger.debug(f"📋 Usando archivo cached: {file_hash[:8]}...")
            return self._uploaded_files_cache[file_hash]
        
        # Determinar tipo de archivo
        file_path_obj = pathlib.Path(file_path)
        file_ext = file_path_obj.suffix.lower()
        
        # Verificar que el archivo sea compatible
        supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
        if file_ext not in supported_extensions:
            raise ValueError(f"Tipo de archivo no soportado: {file_ext}. Soportados: {supported_extensions}")
        
        logger.info(f"📤 Subiendo {file_ext.upper()} con File API: {file_path_obj.name}")
        
        # Subir archivo (File API soporta tanto PDF como imágenes)
        uploaded_file = self.client.files.upload(file=file_path_obj)
        
        # Guardar en cache
        self._uploaded_files_cache[file_hash] = uploaded_file
        logger.info(f"✅ Archivo subido y cached: {file_hash[:8]}... ({file_ext.upper()})")
        
        return uploaded_file
    
    def should_retry_extraction(self, validation_result: Dict[str, Any]) -> bool:
        """
        Determinar si vale la pena re-intentar la extracción.
        
        Criterios:
        - Si hay errores matemáticos en items
        - Si el score de confiabilidad es <= 0.8
        - Si hay más de 3 errores de validación
        
        Args:
            validation_result: Resultado de la validación
        
        Returns:
            True si se recomienda re-extraer
        """
        score = validation_result.get("validation_score", 0)
        errors = validation_result.get("validation_errors", [])
        
        # Criterio 1: Score no óptimo (threshold ajustado a 0.8)
        if score <= 0.8:
            logger.info(f"🔄 Re-extracción recomendada: score no óptimo ({score:.2%}, threshold: 80%)")
            return True
        
        # Criterio 2: Muchos errores
        if len(errors) >= 3:
            logger.info(f"🔄 Re-extracción recomendada: {len(errors)} errores detectados")
            return True
        
        # Criterio 3: Errores matemáticos específicos
        error_keywords = ["Subtotal incorrecto", "Suma de items", "Total calculado", "cantidad", "precio"]
        math_errors = [e for e in errors if any(kw in e for kw in error_keywords)]
        
        if len(math_errors) >= 2:
            logger.info(f"🔄 Re-extracción recomendada: {len(math_errors)} errores matemáticos")
            return True
        
        logger.debug(f"✅ Re-extracción no necesaria: score={score:.2%}, errors={len(errors)}")
        return False
    
    def build_correction_prompt(
        self, 
        original_data: Dict[str, Any], 
        validation_result: Dict[str, Any]
    ) -> str:
        """
        Construir un prompt con contexto de errores para re-extracción.
        
        Args:
            original_data: Datos extraídos originalmente por LlamaExtract
            validation_result: Errores detectados
        
        Returns:
            Prompt enriquecido con contexto
        """
        errors = validation_result.get("validation_errors", [])
        
        prompt_parts = [
            "🚨 ATENCIÓN: La extracción automática anterior tuvo ERRORES MATEMÁTICOS.",
            "",
            "📋 ERRORES DETECTADOS EN LA PRIMERA EXTRACCIÓN:",
        ]
        
        for i, error in enumerate(errors[:10], 1):  # Max 10 errores
            prompt_parts.append(f"  {i}. {error}")
        
        # AGREGAR CONTEXTO: Mostrar qué extrajo LlamaExtract
        prompt_parts.extend([
            "",
            "📊 DATOS EXTRAÍDOS POR LA PRIMERA EXTRACCIÓN (CON ERRORES):",
            "",
        ])
        
        # Mostrar items extraídos (con errores)
        if "items" in original_data:
            items = original_data["items"]
            prompt_parts.append(f"Items extraídos ({len(items)} items):")
            for i, item in enumerate(items[:5], 1):  # Max 5 items como ejemplo
                codigo = item.get('codigo', 'N/A')
                desc = item.get('descripcion', 'N/A')[:30]  # Truncar a 30 chars
                cant = item.get('cantidad', 0)
                precio = item.get('precio_unitario', 0)
                subtotal = item.get('subtotal', 0)
                # Calcular si está correcto
                esperado = cant * precio
                ok = "✅" if abs(esperado - subtotal) < 0.01 else "❌"
                prompt_parts.append(
                    f"  {i}. {ok} {codigo} | {desc}... | cant:{cant} × ${precio:,.2f} = ${subtotal:,.2f}"
                )
            if len(items) > 5:
                prompt_parts.append(f"  ... y {len(items) - 5} items más")
        
        # Mostrar totales extraídos (con errores)
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
            "📸 NUEVA EXTRACCIÓN - INSTRUCCIONES CRÍTICAS:",
            "=" * 60,
            "",
            "🎯 TU TAREA: Re-extraer CORRECTAMENTE todos los datos, corrigiendo los errores anteriores.",
            "",
            "🔍 TABLA DE ITEMS:",
            "1. Revisa CUIDADOSAMENTE cada FILA de la tabla de items",
            "2. Cada FILA = UN item (NO dupliques items)",
            "3. Para CADA item verifica: cantidad × precio_unitario = subtotal",
            "4. NO pongas precios en 'descripcion' - solo texto descriptivo",
            "5. NO pongas descripciones largas en 'codigo' - solo códigos cortos",
            "6. Si un código o precio no está claro, déjalo vacío (null) - NO ADIVINES",
            "7. Lee COLUMNA POR COLUMNA: código → descripción → cantidad → unidad → precio → subtotal",
            "",
            "💰 CÁLCULOS FISCALES:",
            "8. Verifica que la SUMA de todos los subtotals = subtotal_gravado",
            "9. Calcula correctamente: subtotal_gravado + IVA + percepciones + imp_internos = importe_total",
            "10. Lee TODOS los impuestos del pie de factura (IVA, IIBB, Imp. Internos)",
            "",
            "⚠️ ERRORES COMUNES A EVITAR:",
        ])
        
        # Contexto específico según tipo de errores
        if any("codigo" in e.lower() or "descripcion" in e.lower() for e in errors):
            prompt_parts.append("  ❌ NO mezcles código con descripción")
        
        if any("subtotal" in e.lower() or "cantidad" in e.lower() or "precio" in e.lower() for e in errors):
            prompt_parts.append("  ❌ Verifica CADA multiplicación: cantidad × precio = subtotal")
        
        if any("suma" in e.lower() or "total" in e.lower() for e in errors):
            prompt_parts.append("  ❌ Suma TODOS los items (no dejes ninguno fuera)")
        
        if any("duplicad" in e.lower() for e in errors):
            prompt_parts.append("  ❌ NO dupliques items - cada fila es única")
        
        prompt_parts.extend([
            "",
            "✅ EXTRAE NUEVAMENTE con EXTREMA PRECISIÓN en los cálculos matemáticos.",
            "✅ Si un campo no es legible, déjalo vacío (null) - NUNCA inventes datos.",
            ""
        ])
        
        return "\n".join(prompt_parts)
    
    def retry_extraction_with_gemini(
        self,
        file_path: str,
        original_data: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Re-intentar extracción con Gemini 2.5 Flash y contexto de errores.
        
        Args:
            file_path: Ruta al documento (imagen o PDF)
            original_data: Datos de la primera extracción (LlamaExtract)
            validation_result: Errores detectados por el validator
        
        Returns:
            Nuevos datos extraídos o None si falla
        """
        try:
            logger.info("=" * 80)
            logger.info("🤖 [GeminiCorrector] INICIANDO RE-EXTRACCIÓN CON GEMINI 2.5 FLASH")
            logger.info("=" * 80)
            
            # 1. Subir archivo a Gemini File API
            uploaded_file = self._upload_file_with_cache(file_path)
            logger.info(f"📤 Archivo subido: {uploaded_file.name}")
            
            # 2. Construir prompt con contexto de errores
            correction_prompt = self.build_correction_prompt(original_data, validation_result)
            logger.info(f"📝 Prompt de corrección generado ({len(correction_prompt)} chars)")
            
            # 3. System instruction para contexto argentino
            SYSTEM_INSTRUCTION_CONTADOR = """
Eres un contador público argentino certificado con 25+ años de experiencia especializado en:

🏛️ NORMATIVA ARGENTINA:
- Régimen de facturación electrónica AFIP
- Códigos de comprobantes oficiales (001=Factura A, 006=Factura B, 011=Factura C)
- Condiciones fiscales: Responsable Inscripto, Monotributo, Exento, Consumidor Final
- Impuestos: IVA (21%, 10.5%, 27%, 5%, 2.5%), Percepciones IIBB por provincia, Impuestos Internos

🔧 CORRECCIÓN OCR:
- Corrige errores típicos de OCR: ø→é, rn→m, 0→O, 6→G, S→5, l→I
- CUIT: SIEMPRE formato XX-XXXXXXXX-X (con guiones)
- Números: separa miles con puntos, decimales con coma (ej: 1.234,56)

⚖️ PRECISIÓN MATEMÁTICA CRÍTICA:
- CADA item: cantidad × precio_unitario = subtotal (con precisión de 2 decimales)
- SUMA items: Σ(subtotal) = subtotal_gravado
- TOTAL: subtotal_gravado + IVA + percepciones + imp_internos = importe_total
- SI HAY ERROR MATEMÁTICO, revisa TODOS los números hasta que cuadre

🎯 EXTRACCIÓN DE ITEMS (MUY IMPORTANTE):
- Cada FILA de la tabla = 1 item (NO dupliques)
- Lee de IZQUIERDA a DERECHA: código, descripción, cantidad, unidad, precio, subtotal
- Si hay un campo vacío o ilegible, ponlo como null (NO inventes)
- Preserva el ORDEN de los items tal como aparecen en el documento
"""
            
            # 4. Configurar generación con schema estructurado
            contents = [
                uploaded_file,
                correction_prompt
            ]
            
            config = {
                "system_instruction": SYSTEM_INSTRUCTION_CONTADOR,
                "response_mime_type": "application/json",
                "response_schema": GeminiInvoiceComplete,  # 🎯 Schema Pydantic
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
            logger.debug(f"   response type: {type(response)}")
            logger.debug(f"   has 'parsed': {hasattr(response, 'parsed')}")
            logger.debug(f"   has 'text': {hasattr(response, 'text')}")
            
            if hasattr(response, 'parsed') and response.parsed:
                result_obj = response.parsed
                logger.info("✅ Gemini devolvió respuesta estructurada (response.parsed)")
            else:
                # FALLBACK - Parsear JSON manualmente
                logger.warning("⚠️ response.parsed no disponible, parseando JSON manualmente")
                
                # Verificar que response.text exista y no sea None
                if not hasattr(response, 'text') or response.text is None:
                    logger.error("❌ response.text es None o no existe")
                    logger.error(f"   response attributes: {dir(response)}")
                    
                    # Intentar obtener el contenido de otra forma
                    if hasattr(response, 'candidates') and response.candidates:
                        logger.info("   Intentando extraer de response.candidates...")
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content'):
                            content = candidate.content
                            if hasattr(content, 'parts') and content.parts:
                                text = content.parts[0].text
                                logger.info(f"   ✅ Texto extraído de candidates: {text[:100]}...")
                            else:
                                logger.error("   ❌ No se pudo extraer texto de candidates")
                                return None
                        else:
                            logger.error("   ❌ candidate no tiene 'content'")
                            return None
                    else:
                        logger.error("   ❌ No hay candidates disponibles")
                        return None
                else:
                    text = response.text.strip()
                
                try:
                    response_data = json.loads(text)
                    result_obj = GeminiInvoiceComplete(**response_data)
                    logger.info("✅ JSON parseado manualmente - ÉXITO")
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.error(f"❌ Gemini devolvió JSON inválido: {e}")
                    logger.error(f"Texto recibido: {text[:500]}...")
                    return None
            
            # 7. Convertir de Pydantic a dict
            result = {
                "items": [item.model_dump() for item in result_obj.items],
                "fiscalidad": {
                    "totales": {
                        "subtotal_gravado": result_obj.fiscalidad.subtotal_gravado,
                        "importe_total": result_obj.fiscalidad.importe_total,
                    },
                    "impuestos": {
                        "iva_21": result_obj.fiscalidad.iva_21,
                        "iva_105": result_obj.fiscalidad.iva_105,
                        "iva_27": result_obj.fiscalidad.iva_27,
                        "percepcion_iibb": [{"provincia": "caba", "monto": result_obj.fiscalidad.percepcion_iibb}] if result_obj.fiscalidad.percepcion_iibb > 0 else [],
                        "impuestos_internos": result_obj.fiscalidad.impuestos_internos,
                    }
                }
            }
            
            logger.info(f"✅ Gemini extrajo {len(result['items'])} items correctamente")
            logger.info("=" * 80)
            logger.info("🎉 RE-EXTRACCIÓN COMPLETADA CON GEMINI")
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en re-extracción con Gemini: {str(e)}", exc_info=True)
            return None

