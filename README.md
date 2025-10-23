# Extractor_pasaelticket

Django-based API service for extracting data from Argentine invoices using Llamaindex.

## Features

- **Invoice Document Processing**: Upload and process PDF, JPG, PNG, or DOCX invoice documents
- **Llamaindex Integration**: Uses Llamaindex library for intelligent document extraction
- **Argentine Invoice Support**: Specifically designed to extract data from Argentine invoices including:
  - Invoice number (Número de Factura)
  - Vendor/Seller information (Razón Social, CUIT)
  - Customer/Buyer information
  - Financial data (Subtotal, IVA/VAT, Total)
  - Line items and details
- **RESTful API**: Built with Django REST Framework
- **Admin Interface**: Django admin for managing invoices and extracted data

## Requirements

- Python 3.12+
- Django 5.2+
- OpenAI API key (for Llamaindex)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ngentile92/Extractor_pasaelticket.git
cd Extractor_pasaelticket
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. Run database migrations:
```bash
python manage.py migrate
```

6. Create a superuser (optional, for admin access):
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

## API Endpoints

### Main Endpoint: Process Invoice

**POST** `/api/invoices/process/`

Upload and process an invoice document from Argentina.

**Request:**
- Content-Type: `multipart/form-data`
- Body parameter: `document` (file) - PDF, JPG, PNG, or DOCX file

**Response:**
```json
{
  "id": 1,
  "status": "completed",
  "message": "Invoice processed successfully",
  "data": {
    "id": 1,
    "invoice_number": "0001-00001234",
    "invoice_date": "2024-01-15",
    "vendor_name": "Empresa Ejemplo S.A.",
    "vendor_cuit": "30-12345678-9",
    "customer_name": "Cliente Ejemplo",
    "subtotal": "10000.00",
    "tax_amount": "2100.00",
    "total_amount": "12100.00",
    "currency": "ARS",
    ...
  }
}
```

### List Invoices

**GET** `/api/invoices/`

List all processed invoices with pagination.

### Get Invoice Details

**GET** `/api/invoices/{id}/`

Get details of a specific invoice.

### Reprocess Invoice

**GET** `/api/invoices/{id}/reprocess/`

Reprocess an existing invoice document.

## Project Structure

```
Extractor_pasaelticket/
├── extractor_project/      # Django project configuration
│   ├── settings.py         # Project settings
│   ├── urls.py             # Main URL configuration
│   └── wsgi.py             # WSGI configuration
├── invoice_extractor/      # Main application
│   ├── models.py           # Invoice and InvoiceItem models
│   ├── serializers.py      # DRF serializers
│   ├── services.py         # Llamaindex extraction service
│   ├── views.py            # API views/endpoints
│   ├── admin.py            # Django admin configuration
│   └── urls.py             # App URL configuration
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Configuration

Key environment variables in `.env`:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `OPENAI_API_KEY`: OpenAI API key for Llamaindex (required)
- `LLAMAINDEX_MODEL`: Model to use (default: gpt-3.5-turbo)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CORS_ALLOW_ALL_ORIGINS`: Allow CORS from all origins (True/False)

## Development

### Running Tests

```bash
python manage.py test
```

### Admin Interface

Access the admin interface at `http://localhost:8000/admin/` to:
- View and manage invoices
- Manually review extracted data
- Edit invoice information
- View processing status and errors

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]