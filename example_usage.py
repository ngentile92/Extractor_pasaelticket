#!/usr/bin/env python3
"""
Example script demonstrating how to use the Invoice Extractor API

This script shows how to:
1. Upload and process an invoice document
2. Retrieve invoice details
3. List all invoices
"""

import requests
import json
from pathlib import Path


# API Configuration
API_BASE_URL = "http://localhost:8000/api"


def upload_invoice(file_path):
    """
    Upload and process an invoice document
    
    Args:
        file_path: Path to the invoice document (PDF, JPG, PNG, or DOCX)
    
    Returns:
        dict: API response containing invoice data
    """
    url = f"{API_BASE_URL}/invoices/process/"
    
    with open(file_path, 'rb') as f:
        files = {'document': f}
        response = requests.post(url, files=files)
    
    return response.json()


def get_invoice(invoice_id):
    """
    Get details of a specific invoice
    
    Args:
        invoice_id: ID of the invoice
    
    Returns:
        dict: Invoice data
    """
    url = f"{API_BASE_URL}/invoices/{invoice_id}/"
    response = requests.get(url)
    return response.json()


def list_invoices(page=1):
    """
    List all invoices
    
    Args:
        page: Page number for pagination
    
    Returns:
        dict: List of invoices
    """
    url = f"{API_BASE_URL}/invoices/"
    params = {'page': page}
    response = requests.get(url, params=params)
    return response.json()


def reprocess_invoice(invoice_id):
    """
    Reprocess an existing invoice
    
    Args:
        invoice_id: ID of the invoice to reprocess
    
    Returns:
        dict: Updated invoice data
    """
    url = f"{API_BASE_URL}/invoices/{invoice_id}/reprocess/"
    response = requests.get(url)
    return response.json()


def main():
    """Example usage of the API"""
    
    # Example 1: Upload and process an invoice
    print("Example 1: Uploading an invoice...")
    print("=" * 60)
    
    # Uncomment the following lines when you have an invoice file to test
    # invoice_file = "path/to/your/invoice.pdf"
    # result = upload_invoice(invoice_file)
    # print(json.dumps(result, indent=2))
    # invoice_id = result.get('id')
    
    print("Note: Uncomment the code above and provide a valid invoice file path")
    print()
    
    # Example 2: List all invoices
    print("Example 2: Listing all invoices...")
    print("=" * 60)
    invoices = list_invoices()
    print(json.dumps(invoices, indent=2))
    print()
    
    # Example 3: Get specific invoice details
    # Uncomment when you have a valid invoice_id
    # print("Example 3: Getting invoice details...")
    # print("=" * 60)
    # invoice = get_invoice(invoice_id)
    # print(json.dumps(invoice, indent=2))
    # print()
    
    # Example 4: Reprocess an invoice
    # Uncomment when you have a valid invoice_id
    # print("Example 4: Reprocessing invoice...")
    # print("=" * 60)
    # result = reprocess_invoice(invoice_id)
    # print(json.dumps(result, indent=2))
    

if __name__ == "__main__":
    main()
