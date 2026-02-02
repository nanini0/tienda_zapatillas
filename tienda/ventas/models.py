from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre)
            slug = base_slug
            counter = 1
            while Categoria.objects.filter(slug=slug).exists():  # Corregí esto: era Producto
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.nombre


class Producto(models.Model):
    COLORES_ZAPATILLAS = [
        ('negro', 'Negro'),
        ('blanco', 'Blanco'),
        ('gris', 'Gris'),
        ('Azul', 'Azul'),
        ('Rojo', 'Rojo'),
        ('verde', 'Verde'),
        ('beige', 'Beige'),
        ('amarillo', 'Amarillo'),
        ('otros', 'Otros'),
    ]
    
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    marca = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=40, choices=COLORES_ZAPATILLAS, null=True)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    precio_original = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Precio original",
        help_text="Precio antes del descuento (opcional)"
    )
    
    # Nuevos campos para ofertas
    is_oferta = models.BooleanField(default=False)
    descuento_porcentaje = models.PositiveIntegerField(
        default=0,
        verbose_name="Descuento (%)",
        help_text="Porcentaje de descuento (0-100)"
    )
    fecha_inicio_oferta = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Inicio de oferta"
    )
    fecha_fin_oferta = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Fin de oferta"
    )
    
    # Mantenemos este campo para compatibilidad (imagen principal/thumbnail)
    imagen_principal = models.ImageField(
        upload_to='productos/principales/', 
        blank=True, 
        null=True,
        verbose_name="Imagen principal"
    )
    
    is_active = models.BooleanField(default=True)
    is_recommended = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Generar slug automáticamente si no existe
        if not self.slug:
            base_slug = slugify(self.nombre)
            slug = base_slug
            counter = 1
            while Producto.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Si hay descuento y no hay precio_original, guardar el precio actual como original
        if self.is_oferta and self.descuento_porcentaje > 0 and not self.precio_original:
            self.precio_original = self.precio
        
        # Si se desactiva la oferta, restaurar el precio original
        if not self.is_oferta and self.precio_original:
            self.precio = self.precio_original
            self.descuento_porcentaje = 0
            self.fecha_inicio_oferta = None
            self.fecha_fin_oferta = None
        
        super().save(*args, **kwargs)
    
    @property
    def precio_final(self):
        if not self.is_oferta or self.descuento_porcentaje == 0:
            return self.precio

        ahora = timezone.now()
        if self.fecha_inicio_oferta and self.fecha_fin_oferta:
            if not (self.fecha_inicio_oferta <= ahora <= self.fecha_fin_oferta):
                return self.precio_original or self.precio

        precio_base = self.precio_original or self.precio

        # ✅ todo con Decimal
        porcentaje = Decimal(self.descuento_porcentaje) / Decimal("100")
        descuento = (precio_base * porcentaje)

        precio_final = precio_base - descuento

        # ✅ redondeo a 2 decimales como dinero
        return precio_final.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
    @property
    @property
    def ahorro(self):
        if not self.is_oferta or self.descuento_porcentaje == 0:
            return Decimal("0.00")

        precio_base = self.precio_original or self.precio
        ahorro = precio_base - self.precio_final
        return ahorro.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @property
    def tiene_oferta_vigente(self):
        """
        Verifica si la oferta está activa y vigente
        """
        if not self.is_oferta or self.descuento_porcentaje == 0:
            return False
        
        ahora = timezone.now()
        if self.fecha_inicio_oferta and self.fecha_fin_oferta:
            return self.fecha_inicio_oferta <= ahora <= self.fecha_fin_oferta
        
        return self.is_oferta
    
    def aplicar_descuento(self, porcentaje, fecha_fin=None, fecha_inicio=None):
        """
        Método para aplicar un descuento al producto
        """
        self.is_oferta = True
        self.descuento_porcentaje = min(100, max(0, porcentaje))
        
        if not self.precio_original:
            self.precio_original = self.precio
        
        if fecha_inicio:
            self.fecha_inicio_oferta = fecha_inicio
        elif not self.fecha_inicio_oferta:
            self.fecha_inicio_oferta = timezone.now()
        
        if fecha_fin:
            self.fecha_fin_oferta = fecha_fin
        
        self.save()
    
    def quitar_oferta(self):
        """
        Método para quitar la oferta del producto
        """
        if self.precio_original:
            self.precio = self.precio_original
        
        self.is_oferta = False
        self.descuento_porcentaje = 0
        self.precio_original = None
        self.fecha_inicio_oferta = None
        self.fecha_fin_oferta = None
        self.save()
    
    def __str__(self):
        return self.nombre
    
    # Propiedad para obtener la imagen principal (compatibilidad)
    @property
    def imagen(self):
        """Propiedad para compatibilidad con código existente"""
        if self.imagen_principal:
            return self.imagen_principal
        
        # Si no hay imagen principal, intenta obtener una de las imágenes adicionales
        imagen_principal_rel = self.imagenes.filter(is_principal=True).first()
        if imagen_principal_rel:
            return imagen_principal_rel.imagen
        
        # Si no hay ninguna imagen marcada como principal, toma la primera
        primera_imagen = self.imagenes.first()
        if primera_imagen:
            return primera_imagen.imagen
        
        return None
    
    @property
    def todas_las_imagenes(self):
        """Devuelve todas las imágenes del producto en orden"""
        return self.imagenes.all().order_by('orden')


class ImagenProducto(models.Model):
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name='imagenes',
        verbose_name="Producto asociado"
    )
    
    imagen = models.ImageField(
        upload_to='productos/galeria/%Y/%m/%d/',
        verbose_name="Archivo de imagen"
    )
    
    orden = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden de visualización",
        help_text="Número que determina el orden de las imágenes (menor = primero)"
    )
    
    is_principal = models.BooleanField(
        default=False,
        verbose_name="¿Es imagen principal?",
        help_text="Marcar si esta es la imagen principal del producto"
    )
    
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Descripción (alt text)",
        help_text="Descripción de la imagen para SEO y accesibilidad"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"
        ordering = ['orden', 'created_at']
        unique_together = [('producto', 'orden')]
    
    def save(self, *args, **kwargs):
        # Si se marca como principal, quitar principal de otras imágenes del mismo producto
        if self.is_principal and self.pk:
            ImagenProducto.objects.filter(
                producto=self.producto, 
                is_principal=True
            ).exclude(pk=self.pk).update(is_principal=False)
        
        # Si es la primera imagen y no tiene orden asignado, asignar orden
        if not self.pk and self.orden == 0:
            ultimo_orden = ImagenProducto.objects.filter(
                producto=self.producto
            ).aggregate(models.Max('orden'))['orden__max']
            self.orden = (ultimo_orden or 0) + 1 if ultimo_orden is not None else 1
        
        super().save(*args, **kwargs)
    
    def clean(self):
        # Validación: solo una imagen principal por producto
        if self.is_principal:
            principales = ImagenProducto.objects.filter(
                producto=self.producto, 
                is_principal=True
            ).exclude(pk=self.pk if self.pk else None)
            
            if principales.exists():
                raise ValidationError(
                    'Ya existe una imagen principal para este producto. '
                    'Desmarque la actual antes de asignar una nueva.'
                )
    
    def __str__(self):
        return f"Imagen de {self.producto.nombre} (Orden: {self.orden})"