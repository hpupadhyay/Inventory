from django.db import models
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from datetime import datetime
from django.forms.models import inlineformset_factory

from .models import (
    ItemMaster, GroupMaster, WarehouseMaster, Contact,
    InwardHeader, InwardItem, OutwardHeader, OutwardItem,
    ProductionHeader, ProductionItem, WarehouseTransferHeader,
    WarehouseTransferItem, DeliveryOutHeader, DeliveryOutItem,
    DeliveryInHeader, DeliveryInItem, StockAdjustmentHeader, StockAdjustmentItem,
    BillOfMaterial, BOMItem, SystemSetting, User, OpeningStock,
    ItemAlias, PartNumberAlias, BarcodeAlias # <-- ADDED BarcodeAlias
)


class ItemMasterForm(forms.ModelForm):
    class Meta:
        model = ItemMaster
        fields = ['name', 'code', 'group', 'unit']

class ItemAliasForm(forms.ModelForm):
    class Meta:
        model = ItemAlias
        fields = ['alias_name']

class PartNumberAliasForm(forms.ModelForm):
    class Meta:
        model = PartNumberAlias
        fields = ['alias_part_number']

# --- NEW: BarcodeAliasForm ---
class BarcodeAliasForm(forms.ModelForm):
    class Meta:
        model = BarcodeAlias
        fields = ['barcode']

# --- INLINE FORMSET FACTORIES ---
ItemAliasFormSet = inlineformset_factory(
    ItemMaster,
    ItemAlias,
    form=ItemAliasForm,
    extra=1,
    can_delete=True
)

PartNumberAliasFormSet = inlineformset_factory(
    ItemMaster,
    PartNumberAlias,
    form=PartNumberAliasForm,
    extra=1,
    can_delete=True
)

# --- NEW: BarcodeAliasFormSet ---
BarcodeAliasFormSet = inlineformset_factory(
    ItemMaster,
    BarcodeAlias,
    form=BarcodeAliasForm,
    extra=1,
    can_delete=True
)
# --- END OF ALIAS FORMSET FACTORIES ---


class GroupMasterForm(forms.ModelForm):
    class Meta:
        model = GroupMaster
        fields = ['name']
        
class WarehouseMasterForm(forms.ModelForm):
    class Meta:
        model = WarehouseMaster
        fields = ['name', 'parent']
        
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'type']

class InwardHeaderForm(forms.ModelForm):
    class Meta:
        model = InwardHeader
        fields = ['transaction_type','date', 'invoice_no', 'contact', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.TextInput(),
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date

# UPDATED: Added 'barcode_alias' field
class InwardItemForm(forms.ModelForm):
    class Meta:
        model = InwardItem
        fields = ['item', 'warehouse', 'quantity', 'barcode_alias'] # <-- ADDED barcode_alias
        
class OutwardHeaderForm(forms.ModelForm):
    class Meta:
        model = OutwardHeader
        fields = ['transaction_type','date', 'invoice_no', 'contact', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.TextInput(),
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date

# UPDATED: Added 'barcode_alias' field
class OutwardItemForm(forms.ModelForm):
    class Meta:
        model = OutwardItem
        fields = ['item', 'warehouse', 'quantity', 'barcode_alias'] # <-- ADDED barcode_alias
        
class ProductionHeaderForm(forms.ModelForm):
    class Meta:
        model = ProductionHeader
        fields = ['date', 'reference_no', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.TextInput(),
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date

class ProductionItemForm(forms.ModelForm):
    class Meta:
        model = ProductionItem
        fields = ['item', 'warehouse', 'quantity']
        
class WarehouseTransferHeaderForm(forms.ModelForm):
    class Meta:
        model = WarehouseTransferHeader
        fields = ['date', 'reference_no', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.TextInput(),
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date

class WarehouseTransferItemForm(forms.ModelForm):
    class Meta:
        model = WarehouseTransferItem
        fields = ['item', 'from_warehouse', 'to_warehouse', 'quantity']

class DeliveryOutHeaderForm(forms.ModelForm):
    class Meta:
        model = DeliveryOutHeader
        fields = ['date', 'reference_no', 'to_person', 'vehicle_number', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.TextInput(),
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date

class DeliveryOutItemForm(forms.ModelForm):
    class Meta:
        model = DeliveryOutItem
        fields = ['item', 'from_warehouse', 'issued_quantity']


class DeliveryInHeaderForm(forms.ModelForm):
    class Meta:
        model = DeliveryInHeader
        fields = ['date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.TextInput(),
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date


class DeliveryInItemForm(forms.ModelForm):
    original_delivery_item = forms.ModelChoiceField(
        queryset=DeliveryOutItem.objects.filter(issued_quantity__gt=models.F('returned_quantity')),
        widget=forms.Select(attrs={'class': 'original-item-select'})
    )

    class Meta:
        model = DeliveryInItem
        fields = ['original_delivery_item', 'to_warehouse', 'returned_quantity']

class StockAdjustmentHeaderForm(forms.ModelForm):
    class Meta:
        model = StockAdjustmentHeader
        fields = ['date', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.TextInput()
        }
    def clean_date(self):
        transaction_date = self.cleaned_data.get('date')
        active_period = SystemSetting.objects.get(name="Active Period")
        
        if not (active_period.start_date <= transaction_date <= active_period.end_date):
            raise forms.ValidationError(
                f"Transaction date must be within the active period ({active_period.start_date.strftime('%d-%m-%Y')} to {active_period.end_date.strftime('%d-%m-%Y')})."
            )
        return transaction_date

class StockAdjustmentItemForm(forms.ModelForm):
    class Meta:
        model = StockAdjustmentItem
        fields = ['item', 'warehouse', 'adjustment_type', 'quantity']

class BOMForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterial
        fields = ['item']

class BOMItemForm(forms.ModelForm):
    class Meta:
        model = BOMItem
        fields = ['item', 'quantity']

class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'role', 'company', 'is_active', 'is_staff', 'can_edit', 'can_delete')

class CustomUserChangeForm(UserChangeForm):
    password = None
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'company', 'is_active', 'is_staff', 'can_edit', 'can_delete')

# UPDATED: Added 'barcode_alias' field
class OpeningStockForm(forms.ModelForm):
    class Meta:
        model = OpeningStock
        fields = ['date', 'item', 'warehouse', 'quantity', 'barcode_alias'] # <-- ADDED barcode_alias
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        item = cleaned_data.get("item")
        warehouse = cleaned_data.get("warehouse")
        
        if date and item and warehouse:
            year = date.year if date.month < 4 else date.year + 1
            start_of_fy = datetime(year - 1, 4, 1).date()
            end_of_fy = datetime(year, 3, 31).date()

            query = OpeningStock.objects.filter(
                item=item,
                warehouse=warehouse,
                date__range=(start_of_fy, end_of_fy)
            )
            
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError(
                    f"An opening stock for '{item.name}' in '{warehouse.name}' already exists for the {year-1}-{year} financial year. Please edit the existing record instead of creating a new one."
                )
                
        return cleaned_data