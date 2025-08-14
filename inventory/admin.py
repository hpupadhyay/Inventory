from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, GroupMaster, WarehouseMaster, Contact, ItemMaster, OpeningStock,
    InwardHeader, InwardItem, OutwardHeader, OutwardItem, ProductionHeader,
    ProductionItem, WarehouseTransferHeader, WarehouseTransferItem,
    DeliveryOutHeader, DeliveryOutItem, DeliveryInHeader, DeliveryInItem,
    StockAdjustmentHeader, StockAdjustmentItem, BillOfMaterial, BOMItem
)

# --- Custom User Admin ---
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {'fields': ('role', 'can_edit', 'can_delete')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('role', 'can_edit', 'can_delete')}),)

# --- Inlines for Transactions ---
class InwardItemInline(admin.TabularInline):
    model = InwardItem
    extra = 0

class OutwardItemInline(admin.TabularInline):
    model = OutwardItem
    extra = 0

class ProductionItemInline(admin.TabularInline):
    model = ProductionItem
    extra = 0

class WarehouseTransferItemInline(admin.TabularInline):
    model = WarehouseTransferItem
    extra = 0

class DeliveryOutItemInline(admin.TabularInline):
    model = DeliveryOutItem
    extra = 0
    
class StockAdjustmentItemInline(admin.TabularInline):
    model = StockAdjustmentItem
    extra = 0

class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1

# --- ModelAdmin Classes ---
@admin.register(InwardHeader)
class InwardHeaderAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'invoice_no', 'contact', 'date')
    inlines = [InwardItemInline]

@admin.register(OutwardHeader)
class OutwardHeaderAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'invoice_no', 'contact', 'date')
    inlines = [OutwardItemInline]

@admin.register(ProductionHeader)
class ProductionHeaderAdmin(admin.ModelAdmin):
    list_display = ('reference_no', 'date', 'created_by')
    inlines = [ProductionItemInline]

@admin.register(WarehouseTransferHeader)
class WarehouseTransferHeaderAdmin(admin.ModelAdmin):
    # ...
    pass

@admin.register(DeliveryOutHeader)
class DeliveryOutHeaderAdmin(admin.ModelAdmin):
    # ...
    pass

@admin.register(StockAdjustmentHeader)
class StockAdjustmentHeaderAdmin(admin.ModelAdmin):
    # ...
    pass

@admin.register(BillOfMaterial)
class BOMAdmin(admin.ModelAdmin):
    list_display = ('item',)
    inlines = [BOMItemInline]

# --- Simple Model Registrations ---
admin.site.register(User, CustomUserAdmin)
admin.site.register(GroupMaster)
admin.site.register(WarehouseMaster)
admin.site.register(Contact)
admin.site.register(ItemMaster)
admin.site.register(OpeningStock)
admin.site.register(DeliveryInHeader)