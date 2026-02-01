from rest_framework.routers import DefaultRouter
from .views_set import ProductoViewSet, CategoriaViewSet

router = DefaultRouter()
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'categorias', CategoriaViewSet, basename='categoria')

urlpatterns = router.urls

