from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet
from .views_batch import InvoiceBatchViewSet

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
    # Batch processing endpoint
    path('invoices/process-batch/', InvoiceBatchViewSet.as_view({'post': 'upload_batch'}), name='invoice-process-batch'),
]
