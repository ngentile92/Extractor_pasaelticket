"""
Service layer for invoice extraction using Llamaindex
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.llms import OpenAI
from llama_index.core import Settings


class InvoiceExtractionService:
    """Service to extract invoice data from documents using Llamaindex"""
    
    def __init__(self):
        """Initialize Llamaindex with configuration"""
        # Configure the LLM
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            Settings.llm = OpenAI(
                model=os.getenv('LLAMAINDEX_MODEL', 'gpt-3.5-turbo'),
                api_key=api_key
            )
    
    def extract_invoice_data(self, file_path: str) -> Dict[str, Any]:
        """
        Extract invoice data from a document file
        
        Args:
            file_path: Path to the invoice document
            
        Returns:
            Dictionary containing extracted invoice data
        """
        try:
            # Load the document
            documents = SimpleDirectoryReader(
                input_files=[file_path]
            ).load_data()
            
            if not documents:
                return {
                    'success': False,
                    'error': 'Failed to load document'
                }
            
            # Create an index from the documents
            index = VectorStoreIndex.from_documents(documents)
            
            # Create a query engine
            query_engine = index.as_query_engine()
            
            # Extract specific fields for Argentine invoices
            extracted_data = self._query_invoice_fields(query_engine)
            
            return {
                'success': True,
                'data': extracted_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _query_invoice_fields(self, query_engine) -> Dict[str, Any]:
        """
        Query the document for specific invoice fields
        
        Args:
            query_engine: Llamaindex query engine
            
        Returns:
            Dictionary with extracted fields
        """
        fields = {}
        
        # Define queries for Argentine invoice fields
        queries = {
            'invoice_number': 'What is the invoice number (Número de Factura)?',
            'invoice_date': 'What is the invoice date (Fecha de Factura)?',
            'vendor_name': 'What is the vendor/seller name (Razón Social)?',
            'vendor_cuit': 'What is the vendor CUIT number (CUIT del vendedor)?',
            'vendor_address': 'What is the vendor address (Domicilio Comercial)?',
            'customer_name': 'What is the customer/buyer name?',
            'customer_cuit': 'What is the customer CUIT number?',
            'customer_address': 'What is the customer address?',
            'subtotal': 'What is the subtotal amount (Subtotal)?',
            'tax_amount': 'What is the IVA/VAT tax amount?',
            'total_amount': 'What is the total amount (Total)?',
            'currency': 'What is the currency used?',
            'payment_terms': 'What are the payment terms (Condiciones de Pago)?',
        }
        
        # Query each field
        for field, query in queries.items():
            try:
                response = query_engine.query(query)
                if response and str(response).strip():
                    fields[field] = str(response).strip()
            except Exception as e:
                fields[field] = None
        
        # Extract line items
        fields['items'] = self._extract_line_items(query_engine)
        
        return fields
    
    def _extract_line_items(self, query_engine) -> list:
        """
        Extract line items from the invoice
        
        Args:
            query_engine: Llamaindex query engine
            
        Returns:
            List of line items
        """
        try:
            items_query = (
                "List all line items from this invoice. "
                "For each item, provide: description, quantity, unit price, and total price. "
                "Format the response as a structured list."
            )
            response = query_engine.query(items_query)
            
            # This is a simplified extraction - in production, you'd parse the response
            # into structured data
            if response and str(response).strip():
                return [{'description': str(response).strip()}]
            
        except Exception:
            pass
        
        return []
    
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
