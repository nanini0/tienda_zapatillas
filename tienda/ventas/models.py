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
            while Categoria.objects.filter(slug=slug).exists():
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
        ('azul', 'Azul'),
        ('rojo', 'Rojo'),
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
    
    def clean(self):
        """Validaciones adicionales"""
        errors = {}
        
        # Validar que descuento_porcentaje esté entre 0 y 100
        if self.descuento_porcentaje > 100:
            errors['descuento_porcentaje'] = 'El descuento no puede ser mayor al 100%'
        
        # Validar fechas de oferta
        if self.fecha_inicio_oferta and self.fecha_fin_oferta:
            if self.fecha_inicio_oferta >= self.fecha_fin_oferta:
                errors['fecha_fin_oferta'] = 'La fecha de fin debe ser posterior a la fecha de inicio'
        
        # Validar que si hay oferta, tenga porcentaje
        if self.is_oferta and self.descuento_porcentaje == 0:
            errors['descuento_porcentaje'] = 'Debe especificar un porcentaje de descuento para la oferta'
        
        if errors:
            raise ValidationError(errors)
    
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
        
        # CORRECCIÓN IMPORTANTE: Manejo correcto de precios con descuento
        if self.is_oferta and self.descuento_porcentaje > 0:
            # Si no existe precio_original, guardar el precio actual como original
            if not self.precio_original:
                self.precio_original = self.precio
            
            # Calcular el nuevo precio con descuento desde precio_original
            porcentaje = Decimal(self.descuento_porcentaje) / Decimal("100")
            descuento = self.precio_original * porcentaje
            nuevo_precio = self.precio_original - descuento
            
            # Actualizar el precio con descuento aplicado
            self.precio = nuevo_precio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Si se desactiva la oferta y hay precio_original, restaurarlo
        elif not self.is_oferta and self.precio_original:
            self.precio = self.precio_original
            self.precio_original = None
            self.descuento_porcentaje = 0
            self.fecha_inicio_oferta = None
            self.fecha_fin_oferta = None
        
        # Validar antes de guardar
        try:
            self.full_clean()
        except ValidationError:
            pass
        
        super().save(*args, **kwargs)
    
    @property
    def precio_final(self):
        """Calcula el precio final considerando ofertas vigentes"""
        # Si no hay oferta o descuento es 0, devolver precio actual
        if not self.is_oferta or self.descuento_porcentaje == 0:
            return self.precio
        
        # Verificar vigencia de la oferta si tiene fechas
        ahora = timezone.now()
        if self.fecha_inicio_oferta and self.fecha_fin_oferta:
            if not (self.fecha_inicio_oferta <= ahora <= self.fecha_fin_oferta):
                # Oferta no vigente, devolver precio original si existe
                return self.precio_original if self.precio_original else self.precio
        
        # CORRECCIÓN: Si no hay precio_original, usar el precio base
        precio_base = self.precio_original if self.precio_original else self.precio
        
        # Calcular precio con descuento
        porcentaje = Decimal(self.descuento_porcentaje) / Decimal("100")
        descuento = precio_base * porcentaje
        precio_final = precio_base - descuento
        
        return precio_final.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @property
    def precio_original_display(self):
        """Devuelve el precio original para mostrar (si existe)"""
        if self.is_oferta and self.descuento_porcentaje > 0 and self.precio_original:
            return self.precio_original
        return None
    
    @property
    def ahorro(self):
        """Calcula la cantidad ahorrada con la oferta"""
        if not self.is_oferta or self.descuento_porcentaje == 0:
            return Decimal("0.00")
        
        # Verificar vigencia si hay fechas
        ahora = timezone.now()
        if self.fecha_inicio_oferta and self.fecha_fin_oferta:
            if not (self.fecha_inicio_oferta <= ahora <= self.fecha_fin_oferta):
                return Decimal("0.00")
        
        precio_base = self.precio_original if self.precio_original else self.precio
        ahorro = precio_base - self.precio_final
        
        return ahorro.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @property
    def tiene_oferta_vigente(self):
        """Verifica si la oferta está activa y vigente"""
        if not self.is_oferta or self.descuento_porcentaje == 0:
            return False
        
        ahora = timezone.now()
        # Si tiene fechas definidas, verificar vigencia
        if self.fecha_inicio_oferta and self.fecha_fin_oferta:
            return self.fecha_inicio_oferta <= ahora <= self.fecha_fin_oferta
        
        # Si no tiene fechas, la oferta está vigente mientras is_oferta sea True
        return True
    
    @property
    def porcentaje_descuento(self):
        """Devuelve el porcentaje de descuento formateado"""
        if not self.tiene_oferta_vigente:
            return "0%"
        return f"{self.descuento_porcentaje}%"
    
    @property
    def descuento_aplicado(self):
        """Calcula el monto del descuento aplicado"""
        if not self.tiene_oferta_vigente:
            return Decimal("0.00")
        
        precio_base = self.precio_original if self.precio_original else self.precio
        porcentaje = Decimal(self.descuento_porcentaje) / Decimal("100")
        descuento = precio_base * porcentaje
        
        return descuento.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def aplicar_descuento(self, porcentaje, fecha_fin=None, fecha_inicio=None):
        """Método para aplicar un descuento al producto"""
        self.is_oferta = True
        self.descuento_porcentaje = min(100, max(0, porcentaje))
        
        # Guardar precio original si no existe
        if not self.precio_original:
            self.precio_original = self.precio
        
        # Configurar fechas
        if fecha_inicio:
            self.fecha_inicio_oferta = fecha_inicio
        elif not self.fecha_inicio_oferta:
            self.fecha_inicio_oferta = timezone.now()
        
        if fecha_fin:
            self.fecha_fin_oferta = fecha_fin
        
        # Calcular nuevo precio con descuento
        porcentaje_decimal = Decimal(self.descuento_porcentaje) / Decimal("100")
        descuento = self.precio_original * porcentaje_decimal
        self.precio = (self.precio_original - descuento).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        self.save()
    
    def quitar_oferta(self, mantener_precio_actual=False):
        """Método para quitar la oferta del producto"""
        if not mantener_precio_actual and self.precio_original:
            self.precio = self.precio_original
        
        self.is_oferta = False
        self.descuento_porcentaje = 0
        self.fecha_inicio_oferta = None
        self.fecha_fin_oferta = None
        
        # Si mantenemos precio actual, no borramos precio_original
        if not mantener_precio_actual:
            self.precio_original = None
        
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
    
    @property
    def esta_en_oferta(self):
        """Alias para compatibilidad"""
        return self.tiene_oferta_vigente
    
    @property
    def mostrar_precio_original(self):
        """Indica si se debe mostrar el precio original tachado"""
        return self.tiene_oferta_vigente and self.precio_original is not None


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
        # Removemos unique_together temporalmente para evitar conflictos
        # unique_together = [('producto', 'orden')]
    
    def save(self, *args, **kwargs):
        # Guardar primero para obtener un ID
        is_new = self.pk is None
        
        # Guardamos el objeto primero
        super().save(*args, **kwargs)
        
        # Solo procesar después de guardar si el producto está guardado
        if self.producto_id:  # Verificar que el producto tenga ID (esté guardado)
            # Si se marca como principal, quitar principal de otras imágenes
            if self.is_principal:
                ImagenProducto.objects.filter(
                    producto_id=self.producto_id, 
                    is_principal=True
                ).exclude(pk=self.pk).update(is_principal=False)
            
            # Si es nuevo y no tiene orden asignado, asignar orden
            if is_new and self.orden == 0:
                ultimo_orden = ImagenProducto.objects.filter(
                    producto_id=self.producto_id
                ).aggregate(models.Max('orden'))['orden__max'] or 0
                self.orden = ultimo_orden + 1
                
                # Actualizar sin llamar a save() recursivamente
                ImagenProducto.objects.filter(pk=self.pk).update(orden=self.orden)
    
    def clean(self):
        """Validaciones que pueden ejecutarse antes de guardar"""
        # Solo validar si el producto tiene ID (está guardado)
        if self.producto_id:
            # Validación: solo una imagen principal por producto
            if self.is_principal:
                query = ImagenProducto.objects.filter(
                    producto_id=self.producto_id, 
                    is_principal=True
                )
                if self.pk:
                    query = query.exclude(pk=self.pk)
                
                if query.exists():
                    raise ValidationError({
                        'is_principal': 'Ya existe una imagen principal para este producto.'
                    })
            
            # Validar que el orden sea único para este producto
            query = ImagenProducto.objects.filter(
                producto_id=self.producto_id,
                orden=self.orden
            )
            if self.pk:
                query = query.exclude(pk=self.pk)
            
            if query.exists():
                raise ValidationError({
                    'orden': 'Ya existe otra imagen con este orden para este producto.'
                })
    
    def __str__(self):
        return f"Imagen de {self.producto.nombre if self.producto_id else 'Producto sin guardar'} (Orden: {self.orden})"