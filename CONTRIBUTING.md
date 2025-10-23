# Contributing to Extractor_pasaelticket

Thank you for your interest in contributing to this project!

## Development Setup

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- Git
- OpenAI API key (for Llamaindex functionality)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ngentile92/Extractor_pasaelticket.git
   cd Extractor_pasaelticket
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your configuration:
   - `SECRET_KEY`: Generate a new Django secret key
   - `OPENAI_API_KEY`: Your OpenAI API key (required for document processing)
   - Other settings as needed

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Running Tests

Run all tests with:
```bash
python manage.py test
```

Run specific test cases:
```bash
python manage.py test invoice_extractor.tests.InvoiceModelTest
```

## Code Quality

### Linting

This project follows Python best practices. Before submitting a PR:

1. Ensure all tests pass
2. Check for security vulnerabilities
3. Follow PEP 8 style guidelines

### Security

Before committing:
- Never commit sensitive data (API keys, secrets)
- Use `.env` for configuration
- Test error handling and input validation

## Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, concise code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   python manage.py test
   python manage.py check
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure all tests pass

## Project Structure

```
Extractor_pasaelticket/
├── extractor_project/      # Django project settings
│   ├── settings.py         # Main configuration
│   ├── urls.py             # Root URL routing
│   └── wsgi.py             # WSGI application
├── invoice_extractor/      # Main application
│   ├── models.py           # Database models
│   ├── views.py            # API views
│   ├── serializers.py      # DRF serializers
│   ├── services.py         # Business logic (Llamaindex)
│   ├── admin.py            # Admin interface
│   └── tests.py            # Test cases
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## API Development Guidelines

When adding new endpoints:

1. Follow REST conventions
2. Use appropriate HTTP methods (GET, POST, PUT, DELETE)
3. Return consistent JSON responses
4. Include proper error handling
5. Add authentication if needed
6. Document the endpoint in code and README

## Testing Guidelines

- Write unit tests for models and services
- Write API tests for views
- Test both success and error cases
- Use Django's TestCase and APITestCase
- Mock external dependencies (like Llamaindex)

## Questions?

If you have questions, please:
- Check existing issues
- Create a new issue with the "question" label
- Reach out to the maintainers

Thank you for contributing!
