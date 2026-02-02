from django.contrib import admin
from .models import Categoria, Producto, ImagenProducto


# ============ INLINE PARA IMÁGENES ============
class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1
    max_num = 3
    fields = ('imagen', 'orden', 'is_principal', 'descripcion')


# ============ ADMIN PARA CATEGORÍA ============
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'productos_count', 'created_at')
    search_fields = ('nombre',)
    ordering = ('-created_at',)
    list_display_links = ('id', 'nombre',)

    def productos_count(self, obj):
        return obj.productos.count()

    productos_count.short_description = 'Productos'


# ============ ADMIN PARA PRODUCTO ============
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombre', 'categoria',
        'precio', 'precio_original',
        'is_oferta', 'descuento_porcentaje',
        'fecha_inicio_oferta', 'fecha_fin_oferta',
        'color', 'is_active', 'is_recommended',
        'created_at'
    )
    list_display_links = ('id', 'nombre',)
    list_select_related = ('categoria',)
    list_editable = ('precio', 'color', 'is_active', 'is_recommended', 'is_oferta', 'descuento_porcentaje')
    date_hierarchy = 'created_at'
    

    list_filter = (
        'categoria',
        'is_active',
        'is_recommended',
        'is_oferta',
        'color',
        'created_at'
    )

    search_fields = (
        'nombre',
        'descripcion',
        'marca',
        'categoria__nombre'
    )

    fieldsets = (
        ('Información Básica', {
            'fields': ('categoria', 'nombre', 'marca', 'descripcion')
        }),
        ('Detalles', {
            'fields': ('color', 'precio', 'imagen_principal')
        }),
        ('Oferta', {
            'fields': (
                'is_oferta',
                'descuento_porcentaje',
                'precio_original',
                'fecha_inicio_oferta',
                'fecha_fin_oferta',
            )
        }),
        ('Estado', {
            'fields': ('is_active', 'is_recommended')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    inlines = [ImagenProductoInline]
    list_per_page = 25

    actions = ['activar_ofertas', 'desactivar_ofertas']

    def activar_ofertas(self, request, queryset):
        count = 0
        for producto in queryset:
            if not producto.is_oferta:
                producto.is_oferta = True
                if not producto.precio_original:
                    producto.precio_original = producto.precio
                producto.save()
                count += 1
        self.message_user(request, f"{count} producto(s) marcado(s) como oferta")

    activar_ofertas.short_description = "Activar oferta"

    def desactivar_ofertas(self, request, queryset):
        count = 0
        for producto in queryset:
            if producto.is_oferta:
                producto.is_oferta = False
                producto.descuento_porcentaje = 0
                producto.fecha_inicio_oferta = None
                producto.fecha_fin_oferta = None
                producto.save()
                count += 1
        self.message_user(request, f"{count} producto(s) quitado(s) de oferta")

    desactivar_ofertas.short_description = "Desactivar oferta"

    def save_model(self, request, obj, form, change):
        # Si hay descuento y no hay precio original, guardarlo
        if obj.is_oferta and obj.descuento_porcentaje > 0 and not obj.precio_original:
            obj.precio_original = obj.precio

        # Si no hay oferta, limpiar campos de oferta
        if not obj.is_oferta:
            obj.descuento_porcentaje = 0
            obj.fecha_inicio_oferta = None
            obj.fecha_fin_oferta = None

        super().save_model(request, obj, form, change)


# ============ ADMIN PARA IMAGENPRODUCTO ============
@admin.register(ImagenProducto)
class ImagenProductoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'producto',
        'orden',
        'is_principal',
        'descripcion',
        'created_at'
    )
    list_display_links = ('id', 'producto',)
    list_filter = (
        'is_principal',
        'producto__categoria',
        'created_at'
    )
    search_fields = (
        'producto__nombre',
        'descripcion',
        'producto__marca'
    )
    list_editable = ('orden', 'is_principal')
    ordering = ('producto', 'orden')
    list_per_page = 25

    fieldsets = (
        ('Información', {
            'fields': ('producto', 'imagen', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('orden', 'is_principal')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    actions = ['marcar_como_principal']

    def marcar_como_principal(self, request, queryset):
        count = 0
        for imagen in queryset:
            imagen.is_principal = True
            imagen.save()
            count += 1
        self.message_user(request, f"{count} imagen(es) marcada(s) como principal")

    marcar_como_principal.short_description = "Marcar como imagen principal"
