from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_batch import InvoiceBatchViewSet
from .views_gemini import InvoiceGeminiViewSet

router = DefaultRouter()
# Endpoint principal: Gemini
router.register(r'invoices-gemini', InvoiceGeminiViewSet, basename='invoice-gemini')
# Alias para compatibilidad (apunta al mismo ViewSet de Gemini)
router.register(r'invoices', InvoiceGeminiViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
    # Batch processing endpoint
    path('invoices/process-batch/', InvoiceBatchViewSet.as_view({'post': 'upload_batch'}), name='invoice-process-batch'),
]
