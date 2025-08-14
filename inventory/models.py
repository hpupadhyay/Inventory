from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    can_edit = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)

class GroupMaster(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class WarehouseMaster(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def __str__(self):
        return self.name

class Contact(models.Model):
    TYPE_CHOICES = (
        ('Supplier', 'Supplier'),
        ('Customer', 'Customer'),
    )
    name = models.CharField(max_length=150, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.type})"

class ItemMaster(models.Model):
    name = models.CharField(max_length=150, help_text="The main name of the item.")
    code = models.CharField(max_length=50, null=True, blank=True, help_text="The primary unique code or SKU for the item.")
    unit = models.CharField(max_length=20, help_text="e.g., KG, PCS, LTR")
    group = models.ForeignKey(GroupMaster, on_delete=models.PROTECT, related_name='items')

    def __str__(self):
        return f"{self.name} ({self.code or 'No Code'})"

class ItemAlias(models.Model):
    """
    Model to store multiple aliases for an item's name.
    """
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='aliases')
    alias_name = models.CharField(max_length=150, unique=True, help_text="An alternative name for the item.")

    def __str__(self):
        return self.alias_name

class PartNumberAlias(models.Model):
    """
    Model to store multiple part numbers or codes for an item.
    """
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='part_number_aliases')
    alias_part_number = models.CharField(max_length=50, unique=True, help_text="An alternative part number or code.")

    def __str__(self):
        return self.alias_part_number
        
class BarcodeAlias(models.Model):
    """
    Model to store multiple barcodes for a single item.
    """
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='barcode_aliases')
    barcode = models.CharField(max_length=255, unique=True, help_text="A unique barcode for the item.")

    def __str__(self):
        return f"{self.item.name} - {self.barcode}"

class OpeningStock(models.Model):
    date = models.DateField()
    item = models.ForeignKey(ItemMaster, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Added for barcode tracking
    barcode_alias = models.ForeignKey('BarcodeAlias', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('date', 'item', 'warehouse')
    def __str__(self):
        return f"Opening Stock on {self.date} for {self.item.name}: {self.quantity}"

class InwardHeader(models.Model):
    TYPE_CHOICES = (
        ('Purchase', 'Purchase'),
        ('Sales Return', 'Sales Return'),
    )
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Purchase')
    date = models.DateField()
    invoice_no = models.CharField(max_length=50)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inward INV-{self.invoice_no} on {self.date}"

class InwardItem(models.Model):
    """An individual line item within an inward transaction."""
    header = models.ForeignKey(InwardHeader, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    # Added for barcode tracking
    barcode_alias = models.ForeignKey('BarcodeAlias', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.item.name} for INV-{self.header.invoice_no}"
        
class OutwardHeader(models.Model):
    TYPE_CHOICES = (
        ('Sale', 'Sale'),
        ('Purchase Return', 'Purchase Return'),
    )
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Sale')
    date = models.DateField()
    invoice_no = models.CharField(max_length=50)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Outward INV-{self.invoice_no} on {self.date}"

class OutwardItem(models.Model):
    """An individual line item within an outward transaction."""
    header = models.ForeignKey(OutwardHeader, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    # Added for barcode tracking
    barcode_alias = models.ForeignKey('BarcodeAlias', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.item.name} for INV-{self.header.invoice_no}"
class ProductionHeader(models.Model):
    date = models.DateField()
    reference_no = models.CharField(max_length=50, unique=True)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='productions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Production Ref-{self.reference_no} on {self.date}"

class ProductionItem(models.Model):
    TYPE_CHOICES = (
        ('Produced', 'Produced'),
        ('Consumed', 'Consumed'),
    )
    header = models.ForeignKey(ProductionHeader, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.quantity} x {self.item.name} ({self.type})"
        

class WarehouseTransferHeader(models.Model):
    date = models.DateField()
    reference_no = models.CharField(max_length=50, unique=True)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='transfers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transfer Ref-{self.reference_no} on {self.date}"

class WarehouseTransferItem(models.Model):
    header = models.ForeignKey(WarehouseTransferHeader, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    from_warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT, related_name='transfers_from')
    to_warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT, related_name='transfers_to')

    def __str__(self):
        return f"{self.quantity} x {self.item.name} from {self.from_warehouse.name}"
        
class DeliveryOutHeader(models.Model):
    date = models.DateField()
    reference_no = models.CharField(max_length=50, unique=True)
    to_person = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name='deliveries_to')
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='deliveries_out')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Material Out Ref-{self.reference_no} to {self.to_person}"

class DeliveryOutItem(models.Model):
    header = models.ForeignKey(DeliveryOutHeader, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    from_warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)
    issued_quantity = models.PositiveIntegerField()
    returned_quantity = models.PositiveIntegerField(default=0)

    @property
    def pending_quantity(self):
        return self.issued_quantity - self.returned_quantity

    def __str__(self):
        return f"{self.issued_quantity} x {self.item.name} from {self.header}"

class DeliveryInHeader(models.Model):
    date = models.DateField()
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='deliveries_in')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Material In on {self.date} (ID: {self.pk})"

class DeliveryInItem(models.Model):
    header = models.ForeignKey(DeliveryInHeader, on_delete=models.CASCADE, related_name='items')
    original_delivery_item = models.ForeignKey(DeliveryOutItem, on_delete=models.PROTECT)
    returned_quantity = models.PositiveIntegerField()
    to_warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.returned_quantity} x {self.original_delivery_item.item.name} returned"


class StockAdjustmentHeader(models.Model):
    date = models.DateField()
    reason = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adjustment on {self.date} (Reason: {self.reason[:20]}...)"

class StockAdjustmentItem(models.Model):
    ADJUSTMENT_TYPE_CHOICES = (('ADD', 'Increase'), ('SUB', 'Decrease'))
    header = models.ForeignKey(StockAdjustmentHeader, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)
    adjustment_type = models.CharField(max_length=3, choices=ADJUSTMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.get_adjustment_type_display()} {self.quantity} of {self.item.name}"

class BillOfMaterial(models.Model):
    item = models.OneToOneField(ItemMaster, on_delete=models.CASCADE, related_name='bom')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BOM for {self.item.name}"

class BOMItem(models.Model):
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ItemMaster, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} of {self.item.name}"

class SystemSetting(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name