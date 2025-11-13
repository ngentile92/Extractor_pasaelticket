from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet
from .views_batch import InvoiceBatchViewSet
from .views_gemini import InvoiceGeminiViewSet

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'invoices-gemini', InvoiceGeminiViewSet, basename='invoice-gemini')

urlpatterns = [
    path('', include(router.urls)),
    # Batch processing endpoint
    path('invoices/process-batch/', InvoiceBatchViewSet.as_view({'post': 'upload_batch'}), name='invoice-process-batch'),
]
