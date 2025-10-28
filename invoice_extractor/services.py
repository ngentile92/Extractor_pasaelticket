"""
Service layer for invoice extraction using LlamaExtract

LlamaExtract is a specialized service from LlamaCloud for structured data extraction
from documents using Pydantic schemas. It provides high-accuracy extraction for
complex documents like Argentine invoices.

Documentation: https://developers.llamaindex.ai/python/cloud/llamaextract/
"""
import os
from typing import Dict, Any, Optional, Type, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from llama_cloud_services.extract import LlamaExtract, SourceText
    LLAMAEXTRACT_AVAILABLE = True
except ImportError:
    LLAMAEXTRACT_AVAILABLE = False
    logger.warning("llama-cloud-services not installed. Install with: pip install llama-cloud-services")

from .schemas import ComprobanteArgentino, ComprobanteSimplificado, SchemaComposer


class InvoiceExtractionService:
    """
    Service to extract Argentine invoice data using LlamaExtract.
    
    This service uses LlamaExtract (LlamaCloud) to perform structured extraction
    from invoice documents (PDF, images, etc.) using Pydantic schemas.
    
    Features:
    - Structured extraction with schema validation
    - Support for complex Argentine tax structures
    - High accuracy for fiscal data
    - Automatic field validation
    - Modular extraction: extract only the segments you need
    
    Environment Variables Required:
    - LLAMAAPI_KEY: LlamaCloud API key (get from https://cloud.llamaindex.ai)
    """
    
    def __init__(self, schema_type: str = "completo", segments: Optional[List[str]] = None):
        """
        Initialize LlamaExtract service.
        
        Args:
            schema_type: Schema complexity level:
                - "completo": Full schema with all fiscal details (ComprobanteArgentino)
                - "simplificado": Simplified schema for basic extraction (ComprobanteSimplificado)
                - "modular": Use modular extraction with selected segments
            segments: List of segments to extract (only used if schema_type="modular"):
                - 'items': Line items / productos
                - 'partes': Emisor y receptor y sus datos
                - 'documento': Datos del documento en sí
                - 'fiscalidad': Totales e impuestos (includes 'totales')
                - 'totales': Totales varios (solo si fiscalidad no está incluida)
                - 'all' or None: Extract everything
        """
        self.schema_type = schema_type
        self.segments = segments
        self.extractor = None
        self.agent = None
        self.schema_composer = None
        
        # Initialize schema composer if modular mode
        if schema_type == "modular":
            self.schema_composer = SchemaComposer(segments=segments)
        
        if not LLAMAEXTRACT_AVAILABLE:
            logger.error("LlamaExtract not available. Install llama-cloud-services package.")
            return
        
        # Get API key from environment
        api_key = os.getenv('LLAMAAPI_KEY')
        if not api_key:
            logger.error("LLAMAAPI_KEY not found in environment variables")
            return
        
        try:
            # Initialize LlamaExtract client with API key
            self.extractor = LlamaExtract(api_key=api_key)
            logger.info("LlamaExtract client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LlamaExtract: {str(e)}")
            return
    
    def get_or_create_agent(self, agent_name: Optional[str] = None) -> Any:
        """
        Get existing extraction agent or create a new one.
        
        Args:
            agent_name: Name for the agent (default: auto-generated)
            
        Returns:
            LlamaExtract agent instance
        """
        if not self.extractor:
            raise RuntimeError("LlamaExtract not initialized properly")
        
        # Use default agent name based on schema type
        if not agent_name:
            if self.schema_type == "modular" and self.schema_composer:
                segments_str = '_'.join(self.schema_composer.get_segment_list())
                agent_name = f"comprobante-argentino-modular-{segments_str}"
            else:
                agent_name = f"comprobante-argentino-{self.schema_type}"
        
        try:
            # Try to get existing agent
            self.agent = self.extractor.get_agent(name=agent_name)
            logger.info(f"Using existing agent: {agent_name}")
        except Exception:
            # Agent doesn't exist, create it
            schema = self._get_schema()
            logger.info(f"Creating new agent: {agent_name}")
            logger.info(f"Schema: {schema.__name__ if hasattr(schema, '__name__') else str(schema)}")
            self.agent = self.extractor.create_agent(
                name=agent_name,
                data_schema=schema
            )
        
        return self.agent
    
    def _get_schema(self) -> Type:
        """Get the appropriate Pydantic schema based on schema_type."""
        if self.schema_type == "simplificado":
            return ComprobanteSimplificado
        elif self.schema_type == "modular":
            if not self.schema_composer:
                raise RuntimeError("Schema composer not initialized for modular extraction")
            return self.schema_composer.get_schema()
        return ComprobanteArgentino
    
    def extract_invoice_data(self, file_path: str, use_agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract invoice data from a document file using LlamaExtract.
        
        This method uses LlamaExtract to perform structured extraction based on
        the Pydantic schema defined (ComprobanteArgentino or ComprobanteSimplificado).
        
        Args:
            file_path: Path to the invoice document (PDF, JPG, PNG, etc.)
            use_agent_name: Optional custom agent name (default: auto-generated)
            
        Returns:
            Dictionary with extraction result:
            {
                'success': bool,
                'data': dict,  # Extracted data matching the schema
                'error': str,  # Error message if failed
                'metadata': dict  # Additional metadata (job_id, etc.)
            }
        """
        if not LLAMAEXTRACT_AVAILABLE:
            return {
                'success': False,
                'error': 'LlamaExtract is not installed. Please install: pip install llama-cloud-services'
            }
        
        if not self.extractor:
            return {
                'success': False,
                'error': 'LlamaExtract not initialized. Check LLAMAAPI_KEY in environment.'
            }
        
        try:
            # Ensure we have an agent
            if not self.agent:
                self.get_or_create_agent(use_agent_name)
            
            # Validate file exists
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            logger.info(f"Starting extraction for file: {file_path}")
            start_time = datetime.now()
            
            # Perform extraction using LlamaExtract
            # The extract() method accepts file paths directly
            result = self.agent.extract(file_path)
            
            extraction_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Extraction completed in {extraction_time:.2f} seconds")
            
            # Process the result
            # LlamaExtract returns an object with .data attribute containing the extracted data
            if result and hasattr(result, 'data'):
                extracted_data = result.data
                
                # Convert Pydantic model to dict if necessary
                if hasattr(extracted_data, 'model_dump'):
                    extracted_data = extracted_data.model_dump()
                elif hasattr(extracted_data, 'dict'):
                    extracted_data = extracted_data.dict()
                
                metadata = {
                    'extraction_time': extraction_time,
                    'schema_type': self.schema_type,
                    'file_name': os.path.basename(file_path),
                    'agent_name': self.agent.name if hasattr(self.agent, 'name') else None
                }
                
                # Add segment information if modular extraction
                if self.schema_type == "modular" and self.schema_composer:
                    metadata['segments'] = self.schema_composer.get_segment_list()
                
                return {
                    'success': True,
                    'data': extracted_data,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'Extraction returned empty result'
                }
            
        except Exception as e:
            logger.exception(f"Error during invoice extraction: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def extract_from_bytes(
        self, 
        file_bytes: bytes, 
        filename: str,
        use_agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract invoice data from file bytes instead of a file path.
        
        Useful for processing uploaded files without saving to disk first.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename (needed for type detection)
            use_agent_name: Optional custom agent name
            
        Returns:
            Dictionary with extraction result (same format as extract_invoice_data)
        """
        if not LLAMAEXTRACT_AVAILABLE:
            return {
                'success': False,
                'error': 'LlamaExtract is not installed.'
            }
        
        if not self.extractor:
            return {
                'success': False,
                'error': 'LlamaExtract not initialized. Check LLAMAAPI_KEY.'
            }
        
        try:
            # Ensure we have an agent
            if not self.agent:
                self.get_or_create_agent(use_agent_name)
            
            logger.info(f"Starting extraction from bytes: {filename}")
            start_time = datetime.now()
            
            # Use SourceText to extract from bytes
            source = SourceText(file=file_bytes, filename=filename)
            result = self.agent.extract(source)
            
            extraction_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Extraction completed in {extraction_time:.2f} seconds")
            
            if result and hasattr(result, 'data'):
                extracted_data = result.data
                
                # Convert Pydantic model to dict
                if hasattr(extracted_data, 'model_dump'):
                    extracted_data = extracted_data.model_dump()
                elif hasattr(extracted_data, 'dict'):
                    extracted_data = extracted_data.dict()
                
                metadata = {
                    'extraction_time': extraction_time,
                    'schema_type': self.schema_type,
                    'file_name': filename
                }
                
                # Add segment information if modular extraction
                if self.schema_type == "modular" and self.schema_composer:
                    metadata['segments'] = self.schema_composer.get_segment_list()
                
                return {
                    'success': True,
                    'data': extracted_data,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'Extraction returned empty result'
                }
            
        except Exception as e:
            logger.exception(f"Error during extraction from bytes: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_agents(self) -> Dict[str, Any]:
        """
        List all available extraction agents.
        
        Returns:
            Dictionary with list of agents or error
        """
        if not self.extractor:
            return {
                'success': False,
                'error': 'LlamaExtract not initialized'
            }
        
        try:
            agents = self.extractor.list_agents()
            return {
                'success': True,
                'agents': agents
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Delete an extraction agent by name.
        
        Args:
            agent_name: Name of the agent to delete
            
        Returns:
            Dictionary with success status
        """
        if not self.extractor:
            return {
                'success': False,
                'error': 'LlamaExtract not initialized'
            }
        
        try:
            agent = self.extractor.get_agent(name=agent_name)
            self.extractor.delete_agent(agent.id)
            return {
                'success': True,
                'message': f'Agent {agent_name} deleted successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def parse_currency(self, amount_str: Optional[str]) -> Optional[float]:
        """Parse currency string to float"""
        if not amount_str:
            return None
        
        try:
            # Remove common currency symbols and thousands separators
            cleaned = amount_str.replace('$', '').replace('.', '').replace(',', '.').strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        # Common date formats in Argentina
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d/%m/%y',
            '%d-%m-%y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                continue
        
        return None
