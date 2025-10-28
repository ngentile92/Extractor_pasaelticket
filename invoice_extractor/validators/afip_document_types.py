#!/usr/bin/env python3
"""
Catálogo completo de tipos de comprobantes AFIP
Basado en la tabla oficial de códigos de comprobantes fiscales
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

@dataclass
class AFIPDocumentType:
    """Representa un tipo de comprobante AFIP"""
    codigo: str
    denominacion: str
    categoria: str  # factura, nota, recibo, etc.
    regimen: str   # A, B, C, M, etc.
    aliases: List[str]  # Variaciones comunes del nombre
    descripcion: str = ""

# Catálogo completo basado en tabla oficial AFIP
AFIP_DOCUMENT_TYPES = {
    # FACTURAS
    "001": AFIPDocumentType(
        codigo="001",
        denominacion="FACTURAS A",
        categoria="factura",
        regimen="A",
        aliases=["FACTURA A", "FACT A", "FA", "FACTURAS A"],
        descripcion="Factura para responsables inscriptos"
    ),
    "002": AFIPDocumentType(
        codigo="002", 
        denominacion="NOTAS DE DEBITO A",
        categoria="nota_debito",
        regimen="A",
        aliases=["NOTA DE DEBITO A", "ND A", "NOTA DEBITO A"],
        descripcion="Nota de débito régimen A"
    ),
    "003": AFIPDocumentType(
        codigo="003",
        denominacion="NOTAS DE CREDITO A", 
        categoria="nota_credito",
        regimen="A",
        aliases=["NOTA DE CREDITO A", "NC A", "NOTA CREDITO A"],
        descripcion="Nota de crédito régimen A"
    ),
    "004": AFIPDocumentType(
        codigo="004",
        denominacion="RECIBOS A",
        categoria="recibo", 
        regimen="A",
        aliases=["RECIBO A"],
        descripcion="Recibo régimen A"
    ),
    "005": AFIPDocumentType(
        codigo="005",
        denominacion="NOTAS DE VENTA AL CONTADO A",
        categoria="nota_venta",
        regimen="A", 
        aliases=["NOTA DE VENTA AL CONTADO A", "NV A"],
        descripcion="Nota de venta al contado A"
    ),
    "006": AFIPDocumentType(
        codigo="006",
        denominacion="FACTURAS B",
        categoria="factura",
        regimen="B",
        aliases=["FACTURA B", "FACT B", "FB", "FACTURAS B"],
        descripcion="Factura para responsables no inscriptos y exentos"
    ),
    "007": AFIPDocumentType(
        codigo="007",
        denominacion="NOTAS DE DEBITO B",
        categoria="nota_debito",
        regimen="B",
        aliases=["NOTA DE DEBITO B", "ND B", "NOTA DEBITO B"],
        descripcion="Nota de débito régimen B"
    ),
    "008": AFIPDocumentType(
        codigo="008",
        denominacion="NOTAS DE CREDITO B",
        categoria="nota_credito", 
        regimen="B",
        aliases=["NOTA DE CREDITO B", "NC B", "NOTA CREDITO B"],
        descripcion="Nota de crédito régimen B"
    ),
    "009": AFIPDocumentType(
        codigo="009",
        denominacion="RECIBOS B",
        categoria="recibo",
        regimen="B", 
        aliases=["RECIBO B"],
        descripcion="Recibo régimen B"
    ),
    "010": AFIPDocumentType(
        codigo="010",
        denominacion="NOTAS DE VENTA AL CONTADO B",
        categoria="nota_venta",
        regimen="B",
        aliases=["NOTA DE VENTA AL CONTADO B", "NV B"], 
        descripcion="Nota de venta al contado B"
    ),
    "011": AFIPDocumentType(
        codigo="011",
        denominacion="FACTURAS C",
        categoria="factura",
        regimen="C",
        aliases=["FACTURA C", "FACT C", "FC", "FACTURAS C"],
        descripcion="Factura para consumidores finales"
    ),
    "012": AFIPDocumentType(
        codigo="012",
        denominacion="NOTAS DE DEBITO C",
        categoria="nota_debito",
        regimen="C",
        aliases=["NOTA DE DEBITO C", "ND C", "NOTA DEBITO C"],
        descripcion="Nota de débito régimen C"
    ),
    "013": AFIPDocumentType(
        codigo="013",
        denominacion="NOTAS DE CREDITO C", 
        categoria="nota_credito",
        regimen="C",
        aliases=["NOTA DE CREDITO C", "NC C", "NOTA CREDITO C"],
        descripcion="Nota de crédito régimen C"
    ),
    "015": AFIPDocumentType(
        codigo="015",
        denominacion="RECIBOS C",
        categoria="recibo",
        regimen="C",
        aliases=["RECIBO C"],
        descripcion="Recibo régimen C"
    ),
    "016": AFIPDocumentType(
        codigo="016",
        denominacion="NOTAS DE VENTA AL CONTADO C",
        categoria="nota_venta", 
        regimen="C",
        aliases=["NOTA DE VENTA AL CONTADO C", "NV C"],
        descripcion="Nota de venta al contado C"
    ),
    "019": AFIPDocumentType(
        codigo="019",
        denominacion="FACTURAS DE EXPORTACION",
        categoria="factura",
        regimen="E",
        aliases=["FACTURA DE EXPORTACION", "FACTURA EXPORTACION", "FE"],
        descripcion="Factura de exportación"
    ),
    "020": AFIPDocumentType(
        codigo="020",
        denominacion="NOTAS DE DEBITO POR OPERACIONES CON EL EXTERIOR",
        categoria="nota_debito",
        regimen="E",
        aliases=["ND EXTERIOR", "NOTA DEBITO EXTERIOR"],
        descripcion="Nota de débito para operaciones con el exterior"
    ),
    "021": AFIPDocumentType(
        codigo="021",
        denominacion="NOTAS DE CREDITO POR OPERACIONES CON EL EXTERIOR", 
        categoria="nota_credito",
        regimen="E",
        aliases=["NC EXTERIOR", "NOTA CREDITO EXTERIOR"],
        descripcion="Nota de crédito para operaciones con el exterior"
    ),
    "022": AFIPDocumentType(
        codigo="022",
        denominacion="FACTURAS - PERMISO EXPORTACION SIMPLIFICADO",
        categoria="factura",
        regimen="E",
        aliases=["FACTURA PES", "PERMISO EXPORTACION SIMPLIFICADO"],
        descripcion="Factura con permiso de exportación simplificado"
    ),
    "030": AFIPDocumentType(
        codigo="030",
        denominacion="COMPROBANTES DE COMPRA DE BIENES USADOS",
        categoria="comprobante_compra",
        regimen="",
        aliases=["COMPRA BIENES USADOS"],
        descripcion="Comprobante de compra de bienes usados"
    ),
    "031": AFIPDocumentType(
        codigo="031",
        denominacion="MANDATO - CONSIGNACION",
        categoria="mandato",
        regimen="",
        aliases=["MANDATO", "CONSIGNACION"],
        descripcion="Mandato o consignación"
    ),
    "032": AFIPDocumentType(
        codigo="032",
        denominacion="COMPROBANTES PARA RECICLAR MATERIALES",
        categoria="comprobante_reciclado",
        regimen="",
        aliases=["RECICLADO", "MATERIALES RECICLADOS"],
        descripcion="Comprobante para reciclado de materiales"
    ),
    "034": AFIPDocumentType(
        codigo="034",
        denominacion="COMPROBANTES A DEL APARTADO A INCISO F RG N° 1415",
        categoria="comprobante_especial",
        regimen="A",
        aliases=["RG 1415 A"],
        descripcion="Comprobante especial RG 1415 apartado A"
    ),
    "035": AFIPDocumentType(
        codigo="035",
        denominacion="COMPROBANTES B DEL ANEXO I, APARTADO A, INC. F) RG N° 1415",
        categoria="comprobante_especial", 
        regimen="B",
        aliases=["RG 1415 B"],
        descripcion="Comprobante especial RG 1415 apartado B"
    ),
    "036": AFIPDocumentType(
        codigo="036",
        denominacion="COMPROBANTES C DEL ANEXO I, APARTADO A, INC. F) RG N° 1415",
        categoria="comprobante_especial",
        regimen="C", 
        aliases=["RG 1415 C"],
        descripcion="Comprobante especial RG 1415 apartado C"
    ),
    "037": AFIPDocumentType(
        codigo="037",
        denominacion="NOTAS DE DEBITO O DOCUMENTO EQUIVALENTE QUE CUMPLAN CON LA R.G. N° 1415",
        categoria="nota_debito",
        regimen="",
        aliases=["ND RG 1415"],
        descripcion="Nota de débito según RG 1415"
    ),
    "038": AFIPDocumentType(
        codigo="038",
        denominacion="NOTAS DE CREDITO O DOCUMENTO EQUIVALENTE QUE CUMPLAN CON LA R.G. N° 1415",
        categoria="nota_credito",
        regimen="",
        aliases=["NC RG 1415"], 
        descripcion="Nota de crédito según RG 1415"
    ),
    "039": AFIPDocumentType(
        codigo="039",
        denominacion="OTROS COMPROBANTES A QUE CUMPLAN CON LA R.G. N° 1415",
        categoria="otros",
        regimen="A",
        aliases=["OTROS RG 1415 A"],
        descripcion="Otros comprobantes A según RG 1415"
    ),
    "040": AFIPDocumentType(
        codigo="040",
        denominacion="OTROS COMPROBANTES B QUE CUMPLAN CON LA R.G. N° 1415",
        categoria="otros",
        regimen="B",
        aliases=["OTROS RG 1415 B"],
        descripcion="Otros comprobantes B según RG 1415"
    ),
    "041": AFIPDocumentType(
        codigo="041",
        denominacion="OTROS COMPROBANTES C QUE CUMPLAN CON LA R.G. N° 1415", 
        categoria="otros",
        regimen="C",
        aliases=["OTROS RG 1415 C"],
        descripcion="Otros comprobantes C según RG 1415"
    ),
    "050": AFIPDocumentType(
        codigo="050",
        denominacion="RECIBO FACTURA A REGIMEN DE FACTURA DE CREDITO",
        categoria="recibo_factura",
        regimen="A",
        aliases=["RECIBO FACTURA A"],
        descripcion="Recibo factura A régimen de factura de crédito"
    ),
    "051": AFIPDocumentType(
        codigo="051",
        denominacion="FACTURAS M",
        categoria="factura",
        regimen="M",
        aliases=["FACTURA M", "FACT M", "FM", "FACTURAS M"],
        descripcion="Factura M"
    ),
    "052": AFIPDocumentType(
        codigo="052",
        denominacion="NOTAS DE DEBITO M",
        categoria="nota_debito",
        regimen="M",
        aliases=["NOTA DE DEBITO M", "ND M", "NOTA DEBITO M"],
        descripcion="Nota de débito M"
    ),
    "053": AFIPDocumentType(
        codigo="053",
        denominacion="NOTAS DE CREDITO M",
        categoria="nota_credito",
        regimen="M",
        aliases=["NOTA DE CREDITO M", "NC M", "NOTA CREDITO M"],
        descripcion="Nota de crédito M"
    ),
    "054": AFIPDocumentType(
        codigo="054",
        denominacion="RECIBOS M",
        categoria="recibo",
        regimen="M",
        aliases=["RECIBO M"],
        descripcion="Recibo M"
    ),
    "055": AFIPDocumentType(
        codigo="055",
        denominacion="NOTAS DE VENTA AL CONTADO M",
        categoria="nota_venta",
        regimen="M",
        aliases=["NOTA DE VENTA AL CONTADO M", "NV M"],
        descripcion="Nota de venta al contado M"
    ),
    "056": AFIPDocumentType(
        codigo="056",
        denominacion="COMPROBANTES M DEL ANEXO I APARTADO A INCF R.G N° 1415",
        categoria="comprobante_especial",
        regimen="M",
        aliases=["RG 1415 M"],
        descripcion="Comprobante M según RG 1415"
    ),
    "057": AFIPDocumentType(
        codigo="057",
        denominacion="OTROS COMPROBANTES M QUE CUMPLAN CON LA R.G N° 1415",
        categoria="otros",
        regimen="M",
        aliases=["OTROS RG 1415 M"],
        descripcion="Otros comprobantes M según RG 1415"
    ),
    "058": AFIPDocumentType(
        codigo="058",
        denominacion="CUENTAS DE VENTA Y LIQUIDO PRODUCTO M",
        categoria="cuenta_venta",
        regimen="M",
        aliases=["CUENTA VENTA M"],
        descripcion="Cuenta de venta y líquido producto M"
    ),
    "059": AFIPDocumentType(
        codigo="059",
        denominacion="LIQUIDACIONES M",
        categoria="liquidacion",
        regimen="M",
        aliases=["LIQUIDACION M"],
        descripcion="Liquidación M"
    ),
    "060": AFIPDocumentType(
        codigo="060",
        denominacion="CUENTAS DE VENTA Y LIQUIDO PRODUCTO A",
        categoria="cuenta_venta",
        regimen="A",
        aliases=["CUENTA VENTA A"],
        descripcion="Cuenta de venta y líquido producto A"
    ),
    "061": AFIPDocumentType(
        codigo="061",
        denominacion="CUENTAS DE VENTA Y LIQUIDO PRODUCTO B",
        categoria="cuenta_venta",
        regimen="B",
        aliases=["CUENTA VENTA B"],
        descripcion="Cuenta de venta y líquido producto B"
    ),
    "063": AFIPDocumentType(
        codigo="063",
        denominacion="LIQUIDACIONES A",
        categoria="liquidacion",
        regimen="A",
        aliases=["LIQUIDACION A"],
        descripcion="Liquidación A"
    ),
    "064": AFIPDocumentType(
        codigo="064",
        denominacion="LIQUIDACIONES B",
        categoria="liquidacion",
        regimen="B",
        aliases=["LIQUIDACION B"],
        descripcion="Liquidación B"
    ),
    "065": AFIPDocumentType(
        codigo="065",
        denominacion="NOTAS DE CREDITO DE COMPROBANTES CON COD. 34, 39, 58, 59, 60, 63, 96, 97",
        categoria="nota_credito",
        regimen="",
        aliases=["NC COMPROBANTES ESPECIALES"],
        descripcion="Nota de crédito de comprobantes especiales"
    ),
    "066": AFIPDocumentType(
        codigo="066",
        denominacion="DESPACHO DE IMPORTACION",
        categoria="despacho",
        regimen="",
        aliases=["DESPACHO IMPORTACION"],
        descripcion="Despacho de importación"
    ),
    "067": AFIPDocumentType(
        codigo="067",
        denominacion="IMPORTACION DE SERVICIOS",
        categoria="importacion",
        regimen="",
        aliases=["IMPORTACION SERVICIOS"],
        descripcion="Importación de servicios"
    ),
    "068": AFIPDocumentType(
        codigo="068",
        denominacion="LIQUIDACION C",
        categoria="liquidacion",
        regimen="C",
        aliases=["LIQUIDACION C"],
        descripcion="Liquidación C"
    ),
    "070": AFIPDocumentType(
        codigo="070",
        denominacion="RECIBOS FACTURA DE CREDITO",
        categoria="recibo_factura",
        regimen="",
        aliases=["RECIBO FACTURA CREDITO"],
        descripcion="Recibo factura de crédito"
    ),
    "071": AFIPDocumentType(
        codigo="071",
        denominacion="CREDITO FISCAL POR CONTRIBUCIONES PATRONALES",
        categoria="credito_fiscal",
        regimen="",
        aliases=["CREDITO FISCAL PATRONALES"],
        descripcion="Crédito fiscal por contribuciones patronales"
    ),
    "073": AFIPDocumentType(
        codigo="073",
        denominacion="FORMULARIO 1116 RT",
        categoria="formulario",
        regimen="",
        aliases=["FORM 1116 RT"],
        descripcion="Formulario 1116 RT"
    ),
    "074": AFIPDocumentType(
        codigo="074",
        denominacion="CARTA DE PORTE PARA EL TRANSPORTE AUTOMOTOR PARA GRANOS",
        categoria="carta_porte",
        regimen="",
        aliases=["CARTA PORTE GRANOS"],
        descripcion="Carta de porte para transporte automotor de granos"
    ),
    "075": AFIPDocumentType(
        codigo="075",
        denominacion="CARTA DE PORTE PARA EL TRANSPORTE FERROVIARIO PARA GRANOS",
        categoria="carta_porte",
        regimen="",
        aliases=["CARTA PORTE FERROVIARIO GRANOS"],
        descripcion="Carta de porte para transporte ferroviario de granos"
    ),
    # Continúan más códigos...
    "080": AFIPDocumentType(
        codigo="080",
        denominacion="COMPROBANTE DIARIO DE CIERRE (ZETA)",
        categoria="comprobante_cierre",
        regimen="",
        aliases=["CIERRE ZETA", "ZETA"],
        descripcion="Comprobante diario de cierre fiscal"
    ),
    "081": AFIPDocumentType(
        codigo="081",
        denominacion="TIQUE FACTURA A - CONTROLADORES FISCALES",
        categoria="tique",
        regimen="A",
        aliases=["TIQUE A", "TICKET A", "TF A", "TIQUE FACTURA A", "TIQUE FACTURA \"A\""],
        descripcion="Tique factura A de controladores fiscales"
    ),
    "082": AFIPDocumentType(
        codigo="082",
        denominacion="TIQUE - FACTURA B",
        categoria="tique",
        regimen="B",
        aliases=["TIQUE B", "TICKET B", "TF B"],
        descripcion="Tique factura B"
    ),
    "083": AFIPDocumentType(
        codigo="083",
        denominacion="TIQUE",
        categoria="tique",
        regimen="C",
        aliases=["TIQUE C", "TICKET C", "TICKET", "TIQUE"],
        descripcion="Tique consumidor final"
    ),
    "084": AFIPDocumentType(
        codigo="084",
        denominacion="COMPROBANTE - FACTURA DE SERVICIOS PUBLICOS - INTERESES FINANCIEROS",
        categoria="factura_servicios",
        regimen="",
        aliases=["FACTURA SERVICIOS PUBLICOS"],
        descripcion="Factura de servicios públicos con intereses financieros"
    ),
    "085": AFIPDocumentType(
        codigo="085",
        denominacion="NOTA DE CREDITO - SERVICIOS PUBLICOS - NOTA DE CREDITO CONTROLADORES FISCALES",
        categoria="nota_credito",
        regimen="",
        aliases=["NC SERVICIOS PUBLICOS"],
        descripcion="Nota de crédito servicios públicos"
    ),
    "086": AFIPDocumentType(
        codigo="086",
        denominacion="NOTA DE DEBITO - SERVICIOS PUBLICOS",
        categoria="nota_debito",
        regimen="",
        aliases=["ND SERVICIOS PUBLICOS"],
        descripcion="Nota de débito servicios públicos"
    ),
    "087": AFIPDocumentType(
        codigo="087",
        denominacion="OTROS COMPROBANTES - SERVICIOS DEL EXTERIOR",
        categoria="otros",
        regimen="",
        aliases=["SERVICIOS EXTERIOR"],
        descripcion="Otros comprobantes servicios del exterior"
    ),
    "088": AFIPDocumentType(
        codigo="088",
        denominacion="OTROS COMPROBANTES - DOCUMENTOS EXCEPTUADOS - NOTAS DE DEBITO / RESUMEN DE DATOS",
        categoria="otros",
        regimen="",
        aliases=["DOCUMENTOS EXCEPTUADOS"],
        descripcion="Documentos exceptuados - resumen de datos"
    ),
    "089": AFIPDocumentType(
        codigo="089",
        denominacion="OTROS COMPROBANTES - DOCUMENTOS EXCEPTUADOS - NOTAS DE DEBITO",
        categoria="nota_debito",
        regimen="",
        aliases=["ND EXCEPTUADOS"],
        descripcion="Nota de débito documentos exceptuados"
    ),
    "090": AFIPDocumentType(
        codigo="090",
        denominacion="OTROS COMPROBANTES - DOCUMENTOS EXCEPTUADOS - NOTAS DE CREDITO",
        categoria="nota_credito",
        regimen="",
        aliases=["NC EXCEPTUADOS"],
        descripcion="Nota de crédito documentos exceptuados"
    ),
    "091": AFIPDocumentType(
        codigo="091",
        denominacion="REMITOS R",
        categoria="remito",
        regimen="R",
        aliases=["REMITO R"],
        descripcion="Remito R"
    ),
    "092": AFIPDocumentType(
        codigo="092",
        denominacion="AJUSTES CONTABLES QUE INCREMENTAN EL DEBITO FISCAL",
        categoria="ajuste_contable",
        regimen="",
        aliases=["AJUSTE DEBITO FISCAL"],
        descripcion="Ajuste contable que incrementa débito fiscal"
    ),
    "093": AFIPDocumentType(
        codigo="093",
        denominacion="AJUSTES CONTABLES QUE DISMINUYEN EL DEBITO FISCAL",
        categoria="ajuste_contable",
        regimen="",
        aliases=["AJUSTE DEBITO FISCAL NEGATIVO"],
        descripcion="Ajuste contable que disminuye débito fiscal"
    ),
    "094": AFIPDocumentType(
        codigo="094",
        denominacion="AJUSTES CONTABLES QUE INCREMENTAN EL CREDITO FISCAL",
        categoria="ajuste_contable",
        regimen="",
        aliases=["AJUSTE CREDITO FISCAL"],
        descripcion="Ajuste contable que incrementa crédito fiscal"
    ),
    "095": AFIPDocumentType(
        codigo="095",
        denominacion="AJUSTES CONTABLES QUE DISMINUYEN EL CREDITO FISCAL",
        categoria="ajuste_contable",
        regimen="",
        aliases=["AJUSTE CREDITO FISCAL NEGATIVO"],
        descripcion="Ajuste contable que disminuye crédito fiscal"
    ),
    "096": AFIPDocumentType(
        codigo="096",
        denominacion="FORMULARIO 1116 B",
        categoria="formulario",
        regimen="",
        aliases=["FORM 1116 B"],
        descripcion="Formulario 1116 B"
    ),
    "097": AFIPDocumentType(
        codigo="097",
        denominacion="FORMULARIO 1116 C",
        categoria="formulario",
        regimen="",
        aliases=["FORM 1116 C"],
        descripcion="Formulario 1116 C"
    ),
    "099": AFIPDocumentType(
        codigo="099",
        denominacion="OTROS COMP QUE NO CUMPLEN CON LA R.G 3419 Y SUS MODIF",
        categoria="otros",
        regimen="",
        aliases=["NO CUMPLE RG 3419"],
        descripcion="Otros comprobantes que no cumplen RG 3419"
    ),
    "101": AFIPDocumentType(
        codigo="101",
        denominacion="AJUSTE ANUAL PROVENIENTE DE LA DJ DELIVA POSITIVO",
        categoria="ajuste_anual",
        regimen="",
        aliases=["AJUSTE ANUAL IVA POSITIVO"],
        descripcion="Ajuste anual IVA positivo"
    ),
    "102": AFIPDocumentType(
        codigo="102",
        denominacion="AJUSTE ANUAL PROVENIENTE DE LA DJ DELIVA NEGATIVO",
        categoria="ajuste_anual",
        regimen="",
        aliases=["AJUSTE ANUAL IVA NEGATIVO"],
        descripcion="Ajuste anual IVA negativo"
    ),
    "103": AFIPDocumentType(
        codigo="103",
        denominacion="NOTA DE ASIGNACION",
        categoria="nota_asignacion",
        regimen="",
        aliases=["NOTA ASIGNACION"],
        descripcion="Nota de asignación"
    ),
    "104": AFIPDocumentType(
        codigo="104",
        denominacion="NOTA DE CREDITO DE ASIGNACION",
        categoria="nota_credito",
        regimen="",
        aliases=["NC ASIGNACION"],
        descripcion="Nota de crédito de asignación"
    )
}

class AFIPDocumentTypeCatalog:
    """Catálogo de tipos de comprobantes AFIP con funciones de búsqueda y validación"""
    
    def __init__(self):
        self.types = AFIP_DOCUMENT_TYPES
        self._build_search_indexes()
    
    def _build_search_indexes(self):
        """Construir índices de búsqueda para optimizar consultas"""
        self.by_denominacion = {}
        self.by_alias = {}
        self.by_categoria = {}
        self.by_regimen = {}
        
        for codigo, doc_type in self.types.items():
            # Índice por denominación (normalizada)
            denominacion_norm = self._normalize_text(doc_type.denominacion)
            self.by_denominacion[denominacion_norm] = codigo
            
            # Índice por aliases
            for alias in doc_type.aliases:
                alias_norm = self._normalize_text(alias)
                if alias_norm not in self.by_alias:
                    self.by_alias[alias_norm] = []
                self.by_alias[alias_norm].append(codigo)
            
            # Índice por categoría
            if doc_type.categoria not in self.by_categoria:
                self.by_categoria[doc_type.categoria] = []
            self.by_categoria[doc_type.categoria].append(codigo)
            
            # Índice por régimen
            if doc_type.regimen and doc_type.regimen not in self.by_regimen:
                self.by_regimen[doc_type.regimen] = []
            if doc_type.regimen:
                self.by_regimen[doc_type.regimen].append(codigo)
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto para búsqueda (sin acentos, mayúsculas, espacios extra)"""
        if not text:
            return ""
        
        # Convertir a mayúsculas y remover espacios extra
        normalized = re.sub(r'\s+', ' ', text.upper().strip())
        
        # Remover acentos comunes
        replacements = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'Ñ': 'N'
        }
        for accented, plain in replacements.items():
            normalized = normalized.replace(accented, plain)
        
        return normalized
    
    def get_by_code(self, codigo: str) -> Optional[AFIPDocumentType]:
        """Buscar tipo de documento por código AFIP"""
        # Normalizar código (remover ceros a la izquierda, etc.)
        codigo_norm = codigo.strip().zfill(3)  # Asegurar 3 dígitos
        return self.types.get(codigo_norm)
    
    def get_by_name(self, nombre: str) -> Optional[Tuple[str, AFIPDocumentType]]:
        """Buscar tipo de documento por denominación o alias"""
        nombre_norm = self._normalize_text(nombre)
        
        # Buscar en denominaciones exactas
        if nombre_norm in self.by_denominacion:
            codigo = self.by_denominacion[nombre_norm]
            return codigo, self.types[codigo]
        
        # Buscar en aliases
        if nombre_norm in self.by_alias:
            # Si hay múltiples matches, devolver el primero
            codigo = self.by_alias[nombre_norm][0]
            return codigo, self.types[codigo]
        
        # Búsqueda parcial en denominaciones
        for denominacion_norm, codigo in self.by_denominacion.items():
            if nombre_norm in denominacion_norm or denominacion_norm in nombre_norm:
                return codigo, self.types[codigo]
        
        # Búsqueda parcial en aliases
        for alias_norm, codigos in self.by_alias.items():
            if nombre_norm in alias_norm or alias_norm in nombre_norm:
                return codigos[0], self.types[codigos[0]]
        
        return None
    
    def validate_match(self, codigo: str, nombre: str) -> Dict:
        """Validar que código y denominación coincidan"""
        result = {
            "is_valid": False,
            "codigo_encontrado": None,
            "denominacion_encontrada": None,
            "match_score": 0.0,
            "inconsistencias": [],
            "sugerencias": []
        }
        
        # Buscar por código
        doc_by_code = self.get_by_code(codigo) if codigo else None
        
        # Buscar por nombre
        name_result = self.get_by_name(nombre) if nombre else None
        doc_by_name = name_result[1] if name_result else None
        codigo_by_name = name_result[0] if name_result else None
        
        # Casos de validación
        if doc_by_code and doc_by_name:
            # Ambos encontrados - verificar coincidencia
            if doc_by_code.codigo == doc_by_name.codigo:
                result["is_valid"] = True
                result["match_score"] = 1.0
                result["codigo_encontrado"] = doc_by_code.codigo
                result["denominacion_encontrada"] = doc_by_code.denominacion
            else:
                # Verificar si la denominación encontrada está en los aliases del código detectado
                nombre_norm = self._normalize_text(nombre)
                aliases_norm = [self._normalize_text(alias) for alias in doc_by_code.aliases]
                
                if nombre_norm in aliases_norm or any(nombre_norm in alias for alias in aliases_norm):
                    # Es un alias válido del código detectado
                    result["is_valid"] = True
                    result["match_score"] = 0.9  # Ligeramente menor por ser alias
                    result["codigo_encontrado"] = doc_by_code.codigo
                    result["denominacion_encontrada"] = doc_by_code.denominacion
                    result["sugerencias"].append(
                        f"'{nombre}' es un alias válido de '{doc_by_code.denominacion}'"
                    )
                else:
                    # Verdadera inconsistencia
                    result["is_valid"] = False
                    result["match_score"] = 0.0
                    result["inconsistencias"].append(
                        f"Código {codigo} corresponde a '{doc_by_code.denominacion}' "
                        f"pero se encontró '{nombre}' que corresponde al código {doc_by_name.codigo}"
                    )
                    result["sugerencias"].extend([
                        f"Verificar si el código correcto es {doc_by_name.codigo}",
                        f"Verificar si la denominación correcta es '{doc_by_code.denominacion}'"
                    ])
        
        elif doc_by_code and not doc_by_name:
            # Solo código válido
            result["is_valid"] = True
            result["match_score"] = 0.7  # Parcial
            result["codigo_encontrado"] = doc_by_code.codigo
            result["denominacion_encontrada"] = doc_by_code.denominacion
            result["sugerencias"].append(
                f"Denominación esperada: '{doc_by_code.denominacion}'"
            )
        
        elif not doc_by_code and doc_by_name:
            # Solo denominación válida
            result["is_valid"] = True
            result["match_score"] = 0.7  # Parcial
            result["codigo_encontrado"] = doc_by_name.codigo
            result["denominacion_encontrada"] = doc_by_name.denominacion
            result["sugerencias"].append(
                f"Código esperado: {doc_by_name.codigo}"
            )
        
        else:
            # Ninguno encontrado
            result["is_valid"] = False
            result["match_score"] = 0.0
            result["inconsistencias"].append(
                f"No se reconoce el código '{codigo}' ni la denominación '{nombre}'"
            )
            result["sugerencias"].append("Verificar que el documento sea un comprobante AFIP válido")
        
        return result
    
    def get_by_category(self, categoria: str) -> List[AFIPDocumentType]:
        """Obtener todos los documentos de una categoría"""
        codigos = self.by_categoria.get(categoria, [])
        return [self.types[codigo] for codigo in codigos]
    
    def get_by_regime(self, regimen: str) -> List[AFIPDocumentType]:
        """Obtener todos los documentos de un régimen (A, B, C, M, E)"""
        codigos = self.by_regimen.get(regimen, [])
        return [self.types[codigo] for codigo in codigos]
    
    def search_fuzzy(self, query: str, limit: int = 5) -> List[Tuple[str, AFIPDocumentType, float]]:
        """Búsqueda difusa que devuelve los mejores matches con score"""
        query_norm = self._normalize_text(query)
        results = []
        
        for codigo, doc_type in self.types.items():
            score = 0.0
            
            # Coincidencia exacta en denominación
            if query_norm == self._normalize_text(doc_type.denominacion):
                score = 1.0
            # Coincidencia parcial en denominación
            elif query_norm in self._normalize_text(doc_type.denominacion):
                score = 0.8
            elif self._normalize_text(doc_type.denominacion) in query_norm:
                score = 0.7
            
            # Coincidencia en aliases
            for alias in doc_type.aliases:
                alias_norm = self._normalize_text(alias)
                if query_norm == alias_norm:
                    score = max(score, 0.9)
                elif query_norm in alias_norm or alias_norm in query_norm:
                    score = max(score, 0.6)
            
            if score > 0:
                results.append((codigo, doc_type, score))
        
        # Ordenar por score descendente y limitar resultados
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]
    
    def get_all_codes(self) -> List[str]:
        """Obtener todos los códigos disponibles"""
        return list(self.types.keys())
    
    def get_categories(self) -> List[str]:
        """Obtener todas las categorías disponibles"""
        return list(self.by_categoria.keys())
    
    def get_regimes(self) -> List[str]:
        """Obtener todos los regímenes disponibles"""
        return list(self.by_regimen.keys())

# Instancia global del catálogo
afip_catalog = AFIPDocumentTypeCatalog()

# Funciones de conveniencia para uso directo
def get_document_type_by_code(codigo: str) -> Optional[AFIPDocumentType]:
    """Función de conveniencia para buscar por código"""
    return afip_catalog.get_by_code(codigo)

def get_document_type_by_name(nombre: str) -> Optional[Tuple[str, AFIPDocumentType]]:
    """Función de conveniencia para buscar por nombre"""
    return afip_catalog.get_by_name(nombre)

def validate_document_type_match(codigo: str, nombre: str) -> Dict:
    """Función de conveniencia para validar coincidencia"""
    return afip_catalog.validate_match(codigo, nombre)

def search_document_types(query: str, limit: int = 5) -> List[Tuple[str, AFIPDocumentType, float]]:
    """Función de conveniencia para búsqueda difusa"""
    return afip_catalog.search_fuzzy(query, limit)

if __name__ == "__main__":
    # Ejemplos de uso
    print("=== CATÁLOGO AFIP - EJEMPLOS DE USO ===\n")
    
    # Buscar por código
    doc = get_document_type_by_code("001")
    if doc:
        print(f"Código 001: {doc.denominacion} (Régimen {doc.regimen})")
    
    # Buscar por nombre
    result = get_document_type_by_name("FACTURA A")
    if result:
        codigo, doc = result
        print(f"'FACTURA A' → Código {codigo}: {doc.denominacion}")
    
    # Validar coincidencia
    validation = validate_document_type_match("001", "FACTURA A")
    print(f"\nValidación 001 + 'FACTURA A': {validation}")
    
    # Búsqueda difusa
    print(f"\nBúsqueda difusa 'factura':")
    results = search_document_types("factura", 3)
    for codigo, doc, score in results:
        print(f"  {codigo}: {doc.denominacion} (score: {score:.2f})")
    
    print(f"\n=== ESTADÍSTICAS ===")
    print(f"Total de tipos: {len(afip_catalog.get_all_codes())}")
    print(f"Categorías: {len(afip_catalog.get_categories())}")
    print(f"Regímenes: {afip_catalog.get_regimes()}")
