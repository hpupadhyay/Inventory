from django.db.models import Sum, Q, F
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.http import JsonResponse, Http404
from django.db import transaction
from django.forms import formset_factory
from django.contrib import messages
from datetime import datetime, date
from django.contrib.auth import views as auth_views
import csv, io
from django.http import HttpResponse, HttpResponseBadRequest

from .models import (
    ItemMaster, GroupMaster, WarehouseMaster, Contact,
    InwardHeader, InwardItem, OutwardHeader, OutwardItem,
    ProductionHeader, ProductionItem, WarehouseTransferHeader,
    WarehouseTransferItem, StockAdjustmentHeader, StockAdjustmentItem,
    DeliveryOutHeader, DeliveryOutItem, DeliveryInHeader, DeliveryInItem,
    BillOfMaterial, BOMItem, SystemSetting, User, OpeningStock,
    ItemAlias, PartNumberAlias, BarcodeAlias
)

from .forms import (
    ItemMasterForm, GroupMasterForm, WarehouseMasterForm, ContactForm,
    InwardHeaderForm, InwardItemForm, OutwardHeaderForm, OutwardItemForm,
    ProductionHeaderForm, ProductionItemForm, WarehouseTransferHeaderForm,
    WarehouseTransferItemForm, StockAdjustmentHeaderForm, StockAdjustmentItemForm,
    DeliveryOutHeaderForm, DeliveryOutItemForm, DeliveryInHeaderForm,
    DeliveryInItemForm, BOMForm, BOMItemForm, SystemSettingForm,
    CustomUserCreationForm, CustomUserChangeForm, OpeningStockForm,
    ItemAliasFormSet, PartNumberAliasFormSet, BarcodeAliasFormSet
)

# --- UTILITY API VIEWS ---
def get_pending_delivery_item_details_api(request):
    item_id = request.GET.get('item_id')
    try:
        # Replace DeliveryItem with the correct model for pending delivery items.
        # This model should contain the item, delivery header, and pending quantity.
        delivery_item = DeliveryItem.objects.get(pk=item_id)
        
        # Format the text to be displayed in the select box
        item_text = f"{delivery_item.item.name} ({delivery_item.delivery_header.reference_number}, {delivery_item.pending_quantity} Pcs)"
        
        return JsonResponse({
            'success': True,
            'id': delivery_item.pk,
            'text': item_text
        })
    except DeliveryItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found.'})

@login_required
def update_multiple_aliases(request, pk):
    item = get_object_or_404(ItemMaster, pk=pk)
    AliasFormSet = formset_factory(ItemAliasForm, extra=1)

    if request.method == 'POST':
        formset = AliasFormSet(request.POST, request.FILES, instance=item, prefix='aliases')
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Aliases updated successfully!')
            return redirect('item_master')
        else:
            messages.error(request, 'Error updating aliases. Please check the form.')
    else:
        formset = AliasFormSet(instance=item, prefix='aliases')

    context = {
        'item': item,
        'formset': formset,
    }
    return render(request, 'your_template_name.html', context)

def get_item_details_api(request):
    """
    API endpoint to get an item's details by its ID.
    Used for populating the select2 dropdown with the correct value after a barcode scan.
    """
    item_id = request.GET.get('item_id')
    try:
        item = ItemMaster.objects.get(pk=item_id)
        return JsonResponse({
            'success': True,
            'id': item.pk,
            'text': f"{item.name} ({item.code})"
        })
    except ItemMaster.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def get_pending_item_by_barcode_api(request):
    """
    API endpoint to find a pending delivery item by barcode and person.
    """
    barcode_text = request.GET.get('barcode')
    person_id = request.GET.get('person_id')

    if not barcode_text or not person_id:
        return JsonResponse({'success': False, 'error': 'Barcode and person ID are required.'})

    try:
        barcode_alias = BarcodeAlias.objects.select_related('item').get(barcode=barcode_text)
        item = barcode_alias.item
        
        delivery_item = DeliveryOutItem.objects.filter(
            item=item,
            header__to_person=person_id,
            returned_quantity__lt=F('issued_quantity')
        ).first()

        if delivery_item:
            return JsonResponse({
                'success': True,
                'original_delivery_item_id': delivery_item.pk
            })
        else:
            return JsonResponse({'success': False, 'error': 'Pending item not found for this barcode and person.'})
    except BarcodeAlias.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item with this barcode does not exist.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def get_item_by_barcode(request):
    """
    Looks up an ItemMaster by a given barcode.
    This is used by the frontend to get the item ID and populate the form fields.
    """
    barcode_text = request.GET.get('barcode', '')
    if not barcode_text:
        return JsonResponse({'error': 'No barcode provided'}, status=400)

    try:
        barcode_alias = BarcodeAlias.objects.select_related('item').get(barcode=barcode_text)
        item = barcode_alias.item
        return JsonResponse({
            'success': True,
            'item_id': item.pk,
            'item_name': item.name,
            'item_code': item.code
        })
    except BarcodeAlias.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found for this barcode'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def download_template(request, section_name):
    """
    This view generates a blank CSV file with the correct headers for a given section.
    """
    if section_name == 'item_master':
        headers = ['Item Name', 'Item Code', 'Group Name', 'Unit', 'Aliases (||-separated)', 'Part Number Aliases (||-separated)', 'Barcode Aliases (||-separated)']
        filename = 'item_master_template.csv'
    elif section_name == 'inward':  # Use 'inward', not 'inward_template'
        headers = ['Date (YYYY-MM-DD)', 'Invoice No.', 'Supplier Name', 'Item Name', 'Warehouse Name', 'Quantity', 'Remarks']
        filename = 'inward_template.csv'
    elif section_name == 'outward':  # Use 'outward', not 'outward_template'
        headers = ['Date (YYYY-MM-DD)', 'Invoice No.', 'Customer Name', 'Item Name', 'Warehouse Name', 'Quantity', 'Remarks']
        filename = 'outward_template.csv'
    elif section_name == 'delivery_out':
        headers = ['Date (YYYY-MM-DD)', 'Ref No.', 'To Person', 'Vehicle Number', 'Item Name', 'From Warehouse', 'Quantity', 'Remarks']
        filename = 'delivery_out_template.csv'
    elif section_name == 'opening_stock':
        headers = ['Date (YYYY-MM-DD)', 'Item Name', 'Warehouse Name', 'Quantity']
        filename = 'opening_stock_template.csv'
    elif section_name == 'stock_adjustment':
        headers = ['Date (YYYY-MM-DD)', 'Reason', 'Item Name', 'Warehouse Name', 'Type (ADD/SUB)', 'Quantity']
        filename = 'stock_adjustment_template.csv'
    else:
        return HttpResponseBadRequest("Invalid section name provided.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    
    # Example rows are good for a template, but make them comments
    if section_name == 'adjustment':
        writer.writerow(['2025-08-05', 'Annual stock count', 'Item A', 'Main Warehouse', 'ADD', '5'])
        writer.writerow(['2025-08-05', 'Annual stock count', 'Item B', 'Main Warehouse', 'SUB', '2'])
    
    return response
    
# --- UTILITY FUNCTIONS ---
def get_current_period():
    try:
        return SystemSetting.objects.get(name='Active Period')
    except SystemSetting.DoesNotExist:
        return None

def is_date_in_period(transaction_date):
    active_period = get_current_period()
    if active_period:
        return active_period.start_date <= transaction_date <= active_period.end_date
    return False

# --- LOGIN & DASHBOARD VIEWS ---
class CustomLoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current financial period
        current_period = get_current_period()
        context['current_period'] = current_period
        
        # Calculate totals for the current financial year
        if current_period:
            start_date = current_period.start_date
            end_date = current_period.end_date
            
            context['total_inward'] = InwardItem.objects.filter(
                header__date__range=(start_date, end_date)
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            context['total_outward'] = OutwardItem.objects.filter(
                header__date__range=(start_date, end_date)
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            context['total_production'] = ProductionItem.objects.filter(
                header__date__range=(start_date, end_date),
                type='Produced'
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0
            
        else:
            context['total_inward'] = 0
            context['total_outward'] = 0
            context['total_production'] = 0

        # Calculate total stock
        # This is a complex query that needs to be optimized for a real application
        # For this example, we will calculate the sum of all Inward and Production, minus all Outward and Consumption
        
        opening_stock = OpeningStock.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_inward_since_beginning = InwardItem.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_produced_since_beginning = ProductionItem.objects.filter(
            type='Produced'
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_outward_since_beginning = OutwardItem.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_consumed_since_beginning = ProductionItem.objects.filter(
            type='Consumed'
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # This is a simplified calculation. Real-world inventory systems are more complex.
        total_stock = (opening_stock + total_inward_since_beginning + total_produced_since_beginning) - (total_outward_since_beginning + total_consumed_since_beginning)
        
        context['total_stock'] = total_stock
        
        return context

# --- MASTER DATA VIEWS ---
class ItemMasterView(LoginRequiredMixin, CreateView):
    model = ItemMaster
    form_class = ItemMasterForm
    template_name = 'inventory/item_master.html'
    success_url = reverse_lazy('item_master')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = ItemMaster.objects.all()
        
        # Pass the formsets to the context
        if self.request.POST:
            context['alias_formset'] = ItemAliasFormSet(self.request.POST, prefix='aliases')
            context['part_number_formset'] = PartNumberAliasFormSet(self.request.POST, prefix='part_numbers')
        else:
            context['alias_formset'] = ItemAliasFormSet(prefix='aliases')
            context['part_number_formset'] = PartNumberAliasFormSet(prefix='part_numbers')

        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        alias_formset = context['alias_formset']
        part_number_formset = context['part_number_formset']

        if form.is_valid() and alias_formset.is_valid() and part_number_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                alias_formset.instance = self.object
                alias_formset.save()
                part_number_formset.instance = self.object
                part_number_formset.save()
                messages.success(self.request, "Item and its aliases saved successfully!")
            return redirect(self.success_url)
        
        messages.error(self.request, "Error saving item. Please check the form.")
        return self.render_to_response(context)


class ItemUpdateView(LoginRequiredMixin, UpdateView):
    model = ItemMaster
    form_class = ItemMasterForm
    template_name = 'inventory/item_edit.html'
    success_url = reverse_lazy('item_master')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['alias_formset'] = ItemAliasFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='aliases')
            context['part_number_formset'] = PartNumberAliasFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='part_numbers')
        else:
            context['alias_formset'] = ItemAliasFormSet(instance=self.object, prefix='aliases')
            context['part_number_formset'] = PartNumberAliasFormSet(instance=self.object, prefix='part_numbers')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        alias_formset = context['alias_formset']
        part_number_formset = context['part_number_formset']

        if form.is_valid() and alias_formset.is_valid() and part_number_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                alias_formset.instance = self.object
                alias_formset.save()
                part_number_formset.instance = self.object
                part_number_formset.save()
                messages.success(self.request, "Item and its aliases updated successfully!")
            return redirect(self.success_url)
        
        messages.error(self.request, "Error updating item. Please check the form.")
        return self.render_to_response(context)

class ItemDeleteView(LoginRequiredMixin, DeleteView):
    model = ItemMaster
    template_name = 'inventory/item_confirm_delete.html'
    success_url = reverse_lazy('item_master')
    
class GroupMasterView(LoginRequiredMixin, CreateView):
    model = GroupMaster
    form_class = GroupMasterForm
    template_name = 'inventory/group_master.html'
    success_url = reverse_lazy('group_master')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = GroupMaster.objects.all()
        return context
class GroupUpdateView(LoginRequiredMixin, UpdateView):
    model = GroupMaster
    form_class = GroupMasterForm
    template_name = 'inventory/group_edit.html'
    success_url = reverse_lazy('group_master')

class GroupDeleteView(LoginRequiredMixin, DeleteView):
    model = GroupMaster
    template_name = 'inventory/group_confirm_delete.html'
    success_url = reverse_lazy('group_master')
    
class WarehouseMasterView(LoginRequiredMixin, CreateView):
    model = WarehouseMaster
    form_class = WarehouseMasterForm
    template_name = 'inventory/warehouse_master.html'
    success_url = reverse_lazy('warehouse_master')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouses'] = WarehouseMaster.objects.all()
        return context
class ContactMasterView(LoginRequiredMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'inventory/contact_master.html'
    success_url = reverse_lazy('contact_master')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contacts'] = Contact.objects.all()
        return context
    
class OpeningStockView(LoginRequiredMixin, CreateView):
    model = OpeningStock
    form_class = OpeningStockForm
    template_name = 'inventory/opening_stock.html'
    success_url = reverse_lazy('opening_stock')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['opening_stocks'] = OpeningStock.objects.all()
        return context
    
class OpeningStockUpdateView(LoginRequiredMixin, UpdateView):
    model = OpeningStock
    form_class = OpeningStockForm
    template_name = 'inventory/opening_stock_edit.html'
    success_url = reverse_lazy('opening_stock')

class OpeningStockDeleteView(LoginRequiredMixin, DeleteView):
    model = OpeningStock
    template_name = 'inventory/opening_stock_confirm_delete.html'
    success_url = reverse_lazy('opening_stock')

# --- TRANSACTION VIEWS ---
class InwardView(LoginRequiredMixin, View):
    template_name = 'inventory/inward.html'

    def get(self, request, *args, **kwargs):
        InwardItemFormSet = formset_factory(InwardItemForm, extra=1)
        header_form = InwardHeaderForm()
        item_formset = InwardItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': InwardHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        InwardItemFormSet = formset_factory(InwardItemForm)
        header_form = InwardHeaderForm(request.POST)
        item_formset = InwardItemFormSet(request.POST)

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    item.save()
                messages.success(request, 'Inward transaction saved successfully!')
                return redirect('inward')
        
        messages.error(request, 'Error saving inward transaction. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': InwardHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)


class InwardUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/inward_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(InwardHeader, pk=pk)
        InwardItemFormSet = formset_factory(InwardItemForm, extra=1)
        header_form = InwardHeaderForm(instance=header)
        item_formset = InwardItemFormSet(prefix='items', queryset=InwardItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(InwardHeader, pk=pk)
        InwardItemFormSet = formset_factory(InwardItemForm)
        header_form = InwardHeaderForm(request.POST, instance=header)
        item_formset = InwardItemFormSet(request.POST, prefix='items', queryset=InwardItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Inward transaction updated successfully!')
                return redirect('inward')
        
        messages.error(request, 'Error updating inward transaction. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)


class InwardDeleteView(LoginRequiredMixin, DeleteView):
    model = InwardHeader
    template_name = 'inventory/inward_confirm_delete.html'
    success_url = reverse_lazy('inward')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Inward transaction deleted successfully.')
        return super().delete(request, *args, **kwargs)

class OutwardView(LoginRequiredMixin, View):
    template_name = 'inventory/outward.html'

    def get(self, request, *args, **kwargs):
        OutwardItemFormSet = formset_factory(OutwardItemForm, extra=1)
        header_form = OutwardHeaderForm()
        item_formset = OutwardItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': OutwardHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        OutwardItemFormSet = formset_factory(OutwardItemForm)
        header_form = OutwardHeaderForm(request.POST)
        item_formset = OutwardItemFormSet(request.POST)

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    item.save()
                messages.success(request, 'Outward transaction saved successfully!')
                return redirect('outward')
        
        messages.error(request, 'Error saving outward transaction. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': OutwardHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)


class OutwardUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/outward_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(OutwardHeader, pk=pk)
        OutwardItemFormSet = formset_factory(OutwardItemForm, extra=1)
        header_form = OutwardHeaderForm(instance=header)
        item_formset = OutwardItemFormSet(prefix='items', queryset=OutwardItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(OutwardHeader, pk=pk)
        OutwardItemFormSet = formset_factory(OutwardItemForm)
        header_form = OutwardHeaderForm(request.POST, instance=header)
        item_formset = OutwardItemFormSet(request.POST, prefix='items', queryset=OutwardItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Outward transaction updated successfully!')
                return redirect('outward')
        
        messages.error(request, 'Error updating outward transaction. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)


class OutwardDeleteView(LoginRequiredMixin, DeleteView):
    model = OutwardHeader
    template_name = 'inventory/outward_confirm_delete.html'
    success_url = reverse_lazy('outward')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Outward transaction deleted successfully.')
        return super().delete(request, *args, **kwargs)

class ProductionView(LoginRequiredMixin, View):
    template_name = 'inventory/production.html'

    def get(self, request, *args, **kwargs):
        ProductionItemFormSet = formset_factory(ProductionItemForm, extra=1)
        header_form = ProductionHeaderForm()
        item_formset = ProductionItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': ProductionHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        ProductionItemFormSet = formset_factory(ProductionItemForm)
        header_form = ProductionHeaderForm(request.POST)
        item_formset = ProductionItemFormSet(request.POST)

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    # The form doesn't have a 'type' field, so we need to set it manually
                    # This is a simplified assumption. Real-world logic would be more complex.
                    item.type = 'Produced' if item.item.group.name == 'Finished Goods' else 'Consumed'
                    item.save()
                messages.success(request, 'Production transaction saved successfully!')
                return redirect('production')
        
        messages.error(request, 'Error saving production transaction. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': ProductionHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

class ProductionUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/production_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(ProductionHeader, pk=pk)
        ProductionItemFormSet = formset_factory(ProductionItemForm, extra=1)
        header_form = ProductionHeaderForm(instance=header)
        item_formset = ProductionItemFormSet(prefix='items', queryset=ProductionItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(ProductionHeader, pk=pk)
        ProductionItemFormSet = formset_factory(ProductionItemForm)
        header_form = ProductionHeaderForm(request.POST, instance=header)
        item_formset = ProductionItemFormSet(request.POST, prefix='items', queryset=ProductionItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Production transaction updated successfully!')
                return redirect('production')
        
        messages.error(request, 'Error updating production transaction. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

class ProductionDeleteView(LoginRequiredMixin, DeleteView):
    model = ProductionHeader
    template_name = 'inventory/production_confirm_delete.html'
    success_url = reverse_lazy('production')
    
class WarehouseTransferView(LoginRequiredMixin, View):
    template_name = 'inventory/warehouse_transfer.html'

    def get(self, request, *args, **kwargs):
        WarehouseTransferItemFormSet = formset_factory(WarehouseTransferItemForm, extra=1)
        header_form = WarehouseTransferHeaderForm()
        item_formset = WarehouseTransferItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': WarehouseTransferHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        WarehouseTransferItemFormSet = formset_factory(WarehouseTransferItemForm)
        header_form = WarehouseTransferHeaderForm(request.POST)
        item_formset = WarehouseTransferItemFormSet(request.POST)

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    item.save()
                messages.success(request, 'Warehouse Transfer saved successfully!')
                return redirect('warehouse_transfer')
        
        messages.error(request, 'Error saving warehouse transfer. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': WarehouseTransferHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

class WarehouseTransferUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/warehouse_transfer_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(WarehouseTransferHeader, pk=pk)
        WarehouseTransferItemFormSet = formset_factory(WarehouseTransferItemForm, extra=1)
        header_form = WarehouseTransferHeaderForm(instance=header)
        item_formset = WarehouseTransferItemFormSet(prefix='items', queryset=WarehouseTransferItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(WarehouseTransferHeader, pk=pk)
        WarehouseTransferItemFormSet = formset_factory(WarehouseTransferItemForm)
        header_form = WarehouseTransferHeaderForm(request.POST, instance=header)
        item_formset = WarehouseTransferItemFormSet(request.POST, prefix='items', queryset=WarehouseTransferItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Warehouse Transfer updated successfully!')
                return redirect('warehouse_transfer')
        
        messages.error(request, 'Error updating warehouse transfer. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

class WarehouseTransferDeleteView(LoginRequiredMixin, DeleteView):
    model = WarehouseTransferHeader
    template_name = 'inventory/warehouse_transfer_delete.html'
    success_url = reverse_lazy('warehouse_transfer')

class StockAdjustmentView(LoginRequiredMixin, View):
    template_name = 'inventory/stock_adjustment.html'

    def get(self, request, *args, **kwargs):
        StockAdjustmentItemFormSet = formset_factory(StockAdjustmentItemForm, extra=1)
        header_form = StockAdjustmentHeaderForm()
        item_formset = StockAdjustmentItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': StockAdjustmentHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        StockAdjustmentItemFormSet = formset_factory(StockAdjustmentItemForm)
        header_form = StockAdjustmentHeaderForm(request.POST)
        item_formset = StockAdjustmentItemFormSet(request.POST)

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    item.save()
                messages.success(request, 'Stock Adjustment saved successfully!')
                return redirect('stock_adjustment')
        
        messages.error(request, 'Error saving stock adjustment. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': StockAdjustmentHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

class StockAdjustmentUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/stock_adjustment_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(StockAdjustmentHeader, pk=pk)
        StockAdjustmentItemFormSet = formset_factory(StockAdjustmentItemForm, extra=1)
        header_form = StockAdjustmentHeaderForm(instance=header)
        item_formset = StockAdjustmentItemFormSet(prefix='items', queryset=StockAdjustmentItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(StockAdjustmentHeader, pk=pk)
        StockAdjustmentItemFormSet = formset_factory(StockAdjustmentItemForm)
        header_form = StockAdjustmentHeaderForm(request.POST, instance=header)
        item_formset = StockAdjustmentItemFormSet(request.POST, prefix='items', queryset=StockAdjustmentItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Stock Adjustment updated successfully!')
                return redirect('stock_adjustment')
        
        messages.error(request, 'Error updating stock adjustment. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

class StockAdjustmentDeleteView(LoginRequiredMixin, DeleteView):
    model = StockAdjustmentHeader
    template_name = 'inventory/stock_adjustment_confirm_delete.html'
    success_url = reverse_lazy('stock_adjustment')

# --- DELIVERY NOTES VIEWS ---
class DeliveryOutView(LoginRequiredMixin, View):
    template_name = 'inventory/delivery_out.html'

    def get(self, request, *args, **kwargs):
        DeliveryOutItemFormSet = formset_factory(DeliveryOutItemForm, extra=1)
        header_form = DeliveryOutHeaderForm()
        item_formset = DeliveryOutItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': DeliveryOutHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        DeliveryOutItemFormSet = formset_factory(DeliveryOutItemForm)
        header_form = DeliveryOutHeaderForm(request.POST)
        item_formset = DeliveryOutItemFormSet(request.POST)

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    item.save()
                messages.success(request, 'Delivery Note Out saved successfully!')
                return redirect('delivery_out')
        
        messages.error(request, 'Error saving delivery note out. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': DeliveryOutHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)

class DeliveryOutUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/delivery_out_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(DeliveryOutHeader, pk=pk)
        DeliveryOutItemFormSet = formset_factory(DeliveryOutItemForm, extra=1)
        header_form = DeliveryOutHeaderForm(instance=header)
        item_formset = DeliveryOutItemFormSet(prefix='items', queryset=DeliveryOutItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(DeliveryOutHeader, pk=pk)
        DeliveryOutItemFormSet = formset_factory(DeliveryOutItemForm)
        header_form = DeliveryOutHeaderForm(request.POST, instance=header)
        item_formset = DeliveryOutItemFormSet(request.POST, prefix='items', queryset=DeliveryOutItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Delivery Note Out updated successfully!')
                return redirect('delivery_out')
        
        messages.error(request, 'Error updating delivery note out. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

class DeliveryOutDeleteView(LoginRequiredMixin, DeleteView):
    model = DeliveryOutHeader
    template_name = 'inventory/delivery_out_confirm_delete.html'
    success_url = reverse_lazy('delivery_out')
    
class DeliveryInView(LoginRequiredMixin, View):
    template_name = 'inventory/delivery_in.html'

    def get(self, request, *args, **kwargs):
        DeliveryInItemFormSet = formset_factory(DeliveryInItemForm, extra=1)
        header_form = DeliveryInHeaderForm()
        item_formset = DeliveryInItemFormSet()
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': DeliveryInHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)
        
    def post(self, request, *args, **kwargs):
        DeliveryInItemFormSet = formset_factory(DeliveryInItemForm)
        header_form = DeliveryInHeaderForm(request.POST)
        item_formset = DeliveryInItemFormSet(request.POST)
        
        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header = header_form.save(commit=False)
                header.created_by = request.user
                header.save()
                for item_form in item_formset:
                    item = item_form.save(commit=False)
                    item.header = header
                    item.save()
                    # UPDATE THE ORIGINAL DeliveryOutItem's returned_quantity
                    original_item = item.original_delivery_item
                    original_item.returned_quantity += item.returned_quantity
                    original_item.save()
                messages.success(request, 'Delivery Note In saved successfully!')
                return redirect('delivery_in')

        messages.error(request, 'Error saving delivery note in. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'transactions': DeliveryInHeader.objects.all().order_by('-date')[:10]
        }
        return render(request, self.template_name, context)


class DeliveryInUpdateView(LoginRequiredMixin, View):
    template_name = 'inventory/delivery_in_edit.html'

    def get(self, request, pk, *args, **kwargs):
        header = get_object_or_404(DeliveryInHeader, pk=pk)
        DeliveryInItemFormSet = formset_factory(DeliveryInItemForm, extra=1)
        header_form = DeliveryInHeaderForm(instance=header)
        item_formset = DeliveryInItemFormSet(prefix='items', queryset=DeliveryInItem.objects.filter(header=header))
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        header = get_object_or_404(DeliveryInHeader, pk=pk)
        DeliveryInItemFormSet = formset_factory(DeliveryInItemForm)
        header_form = DeliveryInHeaderForm(request.POST, instance=header)
        item_formset = DeliveryInItemFormSet(request.POST, prefix='items', queryset=DeliveryInItem.objects.filter(header=header))

        if header_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                header_form.save()
                item_formset.save()
                messages.success(request, 'Delivery Note In updated successfully!')
                return redirect('delivery_in')
        
        messages.error(request, 'Error updating delivery note in. Please check the forms.')
        context = {
            'header_form': header_form,
            'item_formset': item_formset,
            'header': header,
        }
        return render(request, self.template_name, context)

class DeliveryInDeleteView(LoginRequiredMixin, DeleteView):
    model = DeliveryInHeader
    template_name = 'inventory/delivery_in_confirm_delete.html'
    success_url = reverse_lazy('delivery_in')

# --- REPORTS VIEWS ---
class StockReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/stock_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        items = ItemMaster.objects.all()
        report_data = []

        for item in items:
            opening_stock = OpeningStock.objects.filter(item=item).aggregate(Sum('quantity'))['quantity__sum'] or 0
            inward_qty = InwardItem.objects.filter(item=item).aggregate(Sum('quantity'))['quantity__sum'] or 0
            outward_qty = OutwardItem.objects.filter(item=item).aggregate(Sum('quantity'))['quantity__sum'] or 0
            produced_qty = ProductionItem.objects.filter(item=item, type='Produced').aggregate(Sum('quantity'))['quantity__sum'] or 0
            consumed_qty = ProductionItem.objects.filter(item=item, type='Consumed').aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            stock = opening_stock + inward_qty + produced_qty - outward_qty - consumed_qty
            
            report_data.append({
                'item': item,
                'opening_stock': opening_stock,
                'inward_qty': inward_qty,
                'outward_qty': outward_qty,
                'produced_qty': produced_qty,
                'consumed_qty': consumed_qty,
                'closing_stock': stock,
            })
        
        context['report_data'] = report_data
        return context

class StockReportDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/stock_report_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item_id = self.request.GET.get('item_id')
        warehouse_id = self.request.GET.get('warehouse_id')
        
        if not item_id or not warehouse_id:
            context['error'] = "Item and Warehouse are required."
            return context

        item = get_object_or_404(ItemMaster, id=item_id)
        warehouse = get_object_or_404(WarehouseMaster, id=warehouse_id)
        
        # Get all relevant transactions for the item and warehouse
        transactions = []
        
        # Opening Stock
        opening_stock = OpeningStock.objects.filter(item=item, warehouse=warehouse).first()
        if opening_stock:
            transactions.append({
                'date': opening_stock.date,
                'type': 'Opening Stock',
                'reference_no': 'N/A',
                'in': opening_stock.quantity,
                'out': 0,
                'balance': opening_stock.quantity,
            })

        # Inward Items
        inward_items = InwardItem.objects.filter(item=item, warehouse=warehouse).order_by('header__date')
        for i in inward_items:
            transactions.append({
                'date': i.header.date,
                'type': 'Inward',
                'reference_no': i.header.invoice_no,
                'in': i.quantity,
                'out': 0,
                'balance': 0,
            })
            
        # Outward Items
        outward_items = OutwardItem.objects.filter(item=item, warehouse=warehouse).order_by('header__date')
        for o in outward_items:
            transactions.append({
                'date': o.header.date,
                'type': 'Outward',
                'reference_no': o.header.invoice_no,
                'in': 0,
                'out': o.quantity,
                'balance': 0,
            })
            
        # Production Items (Produced)
        produced_items = ProductionItem.objects.filter(item=item, warehouse=warehouse, type='Produced').order_by('header__date')
        for p in produced_items:
            transactions.append({
                'date': p.header.date,
                'type': 'Production (Produced)',
                'reference_no': p.header.reference_no,
                'in': p.quantity,
                'out': 0,
                'balance': 0,
            })
            
        # Production Items (Consumed)
        consumed_items = ProductionItem.objects.filter(item=item, warehouse=warehouse, type='Consumed').order_by('header__date')
        for c in consumed_items:
            transactions.append({
                'date': c.header.date,
                'type': 'Production (Consumed)',
                'reference_no': c.header.reference_no,
                'in': 0,
                'out': c.quantity,
                'balance': 0,
            })

        # Warehouse Transfers (In)
        transfers_in = WarehouseTransferItem.objects.filter(item=item, to_warehouse=warehouse).order_by('header__date')
        for ti in transfers_in:
            transactions.append({
                'date': ti.header.date,
                'type': 'Transfer In',
                'reference_no': ti.header.reference_no,
                'in': ti.quantity,
                'out': 0,
                'balance': 0,
            })
            
        # Warehouse Transfers (Out)
        transfers_out = WarehouseTransferItem.objects.filter(item=item, from_warehouse=warehouse).order_by('header__date')
        for to in transfers_out:
            transactions.append({
                'date': to.header.date,
                'type': 'Transfer Out',
                'reference_no': to.header.reference_no,
                'in': 0,
                'out': to.quantity,
                'balance': 0,
            })
            
        # Stock Adjustments
        adjustments = StockAdjustmentItem.objects.filter(item=item, warehouse=warehouse).order_by('header__date')
        for adj in adjustments:
            in_qty = adj.quantity if adj.adjustment_type == 'ADD' else 0
            out_qty = adj.quantity if adj.adjustment_type == 'SUB' else 0
            transactions.append({
                'date': adj.header.date,
                'type': f'Adjustment ({adj.get_adjustment_type_display()})',
                'reference_no': 'N/A',
                'in': in_qty,
                'out': out_qty,
                'balance': 0,
            })
            
        # Sort all transactions by date
        transactions.sort(key=lambda x: x['date'])
        
        # Calculate running balance
        balance = 0
        for transaction in transactions:
            balance += transaction['in']
            balance -= transaction['out']
            transaction['balance'] = balance
            
        context['item'] = item
        context['warehouse'] = warehouse
        context['transactions'] = transactions
        
        return context

class InwardReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/inward_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inward_headers'] = InwardHeader.objects.all().order_by('-date')
        return context

class OutwardReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/outward_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['outward_headers'] = OutwardHeader.objects.all().order_by('-date')
        return context
        
class ProductionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/production_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['production_headers'] = ProductionHeader.objects.all().order_by('-date')
        return context

class WarehouseTransferReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/warehouse_transfer_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transfer_headers'] = WarehouseTransferHeader.objects.all().order_by('-date')
        return context

class DeliveryNoteReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/delivery_note_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delivery_out_headers'] = DeliveryOutHeader.objects.all().order_by('-date')
        context['delivery_in_headers'] = DeliveryInHeader.objects.all().order_by('-date')
        return context

class StockAdjustmentReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/stock_adjustment_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['adjustment_headers'] = StockAdjustmentHeader.objects.all().order_by('-date')
        return context

class PendingDeliveryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/pending_delivery_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_items'] = DeliveryOutItem.objects.filter(
            issued_quantity__gt=F('returned_quantity')
        ).select_related('header__to_person', 'item', 'from_warehouse')
        return context

# --- SETTINGS & MANAGEMENT VIEWS ---
class BOMView(LoginRequiredMixin, View):
    template_name = 'inventory/bom.html'

    def get(self, request, *args, **kwargs):
        BOMItemFormSet = formset_factory(BOMItemForm, extra=1, can_delete=True)
        bom_form = BOMForm()
        bom_item_formset = BOMItemFormSet()
        context = {
            'bom_form': bom_form,
            'bom_item_formset': bom_item_formset,
            'boms': BillOfMaterial.objects.all()
        }
        return render(request, self.template_name, context)
        
    def post(self, request, *args, **kwargs):
        BOMItemFormSet = formset_factory(BOMItemForm)
        bom_form = BOMForm(request.POST)
        bom_item_formset = BOMItemFormSet(request.POST)

        if bom_form.is_valid() and bom_item_formset.is_valid():
            with transaction.atomic():
                bom = bom_form.save()
                for item_form in bom_item_formset:
                    item = item_form.save(commit=False)
                    item.bom = bom
                    item.save()
                messages.success(request, 'BOM saved successfully!')
                return redirect('bom_create')
        
        messages.error(request, 'Error saving BOM. Please check the forms.')
        context = {
            'bom_form': bom_form,
            'bom_item_formset': bom_item_formset,
            'boms': BillOfMaterial.objects.all()
        }
        return render(request, self.template_name, context)

class PeriodSettingView(LoginRequiredMixin, View):
    template_name = 'inventory/period_setting.html'

    def get(self, request, *args, **kwargs):
        try:
            active_period = SystemSetting.objects.get(name='Active Period')
            form = SystemSettingForm(instance=active_period)
        except SystemSetting.DoesNotExist:
            form = SystemSettingForm()
            active_period = None
        
        context = {
            'form': form,
            'active_period': active_period,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            active_period = SystemSetting.objects.get(name='Active Period')
            form = SystemSettingForm(request.POST, instance=active_period)
        except SystemSetting.DoesNotExist:
            form = SystemSettingForm(request.POST)
        
        if form.is_valid():
            active_period = form.save(commit=False)
            active_period.name = 'Active Period'
            active_period.save()
            messages.success(request, 'Active period updated successfully!')
            return redirect('period_setting')
        
        messages.error(request, 'Error updating active period. Please check the form.')
        context = {
            'form': form,
            'active_period': SystemSetting.objects.first(),
        }
        return render(request, self.template_name, context)

class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'inventory/user_list.html'
    context_object_name = 'users'

class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'inventory/user_create.html'
    success_url = reverse_lazy('user_list')
    
class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'inventory/user_edit.html'
    success_url = reverse_lazy('user_list')

# --- IMPORT VIEW ---
class ImportView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/import.html'
    
    def post(self, request, *args, **kwargs):
        import_type = request.POST.get('import_type')
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file or not import_type:
            messages.error(request, 'Please select a file and an import type.')
            return redirect('import_page')
            
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string)
        next(reader) # Skip header
        
        try:
            with transaction.atomic():
                if import_type == 'item_master':
                    for row in reader:
                        ItemMaster.objects.create(
                            name=row[0],
                            code=row[1],
                            unit=row[2],
                            group=GroupMaster.objects.get(name=row[3])
                        )
                elif import_type == 'group_master':
                    for row in reader:
                        GroupMaster.objects.create(name=row[0])
                elif import_type == 'warehouse_master':
                    for row in reader:
                        parent = None
                        if row[1]:
                            parent = WarehouseMaster.objects.get(name=row[1])
                        WarehouseMaster.objects.create(name=row[0], parent=parent)
                elif import_type == 'contact_master':
                    for row in reader:
                        Contact.objects.create(name=row[0], type=row[1])
                elif import_type == 'opening_stock':
                    for row in reader:
                        OpeningStock.objects.create(
                            date=datetime.strptime(row[0], '%Y-%m-%d').date(),
                            item=ItemMaster.objects.get(code=row[1]),
                            warehouse=WarehouseMaster.objects.get(name=row[2]),
                            quantity=row[3]
                        )
                else:
                    messages.error(request, 'Invalid import type.')
                    return redirect('import_page')

            messages.success(request, f'{import_type.replace("_", " ").title()} imported successfully!')
        except Exception as e:
            messages.error(request, f'Error during import: {e}')
            
        return redirect('import_page')

# --- API VIEWS ---
@login_required
def get_items_api(request):
    term = request.GET.get('term', '')
    
    # Use Q objects to combine search queries across multiple fields and related models
    if term:
        items = ItemMaster.objects.filter(
            Q(name__icontains=term) | 
            Q(code__icontains=term) |
            Q(aliases__alias_name__icontains=term) |
            Q(part_number_aliases__alias_part_number__icontains=term)
        ).distinct()
    else:
        items = ItemMaster.objects.all()

    results = []
    for item in items:
        results.append({
            'id': item.pk,
            'text': f"{item.name} ({item.code})"
        })
        
    return JsonResponse({'results': results})

@login_required
def get_item_stock_details_api(request):
    """API to get stock details for a specific item."""
    item_id = request.GET.get('item_id')
    if not item_id:
        return JsonResponse({'error': 'item_id is required'}, status=400)

    warehouses = WarehouseMaster.objects.all()
    stock_data = []

    for warehouse in warehouses:
        opening_stock = OpeningStock.objects.filter(item_id=item_id, warehouse=warehouse).aggregate(Sum('quantity'))['quantity__sum'] or 0
        inward_qty = InwardItem.objects.filter(item_id=item_id, warehouse=warehouse).aggregate(Sum('quantity'))['quantity__sum'] or 0
        outward_qty = OutwardItem.objects.filter(item_id=item_id, warehouse=warehouse).aggregate(Sum('quantity'))['quantity__sum'] or 0
        produced_qty = ProductionItem.objects.filter(item_id=item_id, warehouse=warehouse, type='Produced').aggregate(Sum('quantity'))['quantity__sum'] or 0
        consumed_qty = ProductionItem.objects.filter(item_id=item_id, warehouse=warehouse, type='Consumed').aggregate(Sum('quantity'))['quantity__sum'] or 0
        transferred_in_qty = WarehouseTransferItem.objects.filter(item_id=item_id, to_warehouse=warehouse).aggregate(Sum('quantity'))['quantity__sum'] or 0
        transferred_out_qty = WarehouseTransferItem.objects.filter(item_id=item_id, from_warehouse=warehouse).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # Calculate adjustment quantities
        increase_adj_qty = StockAdjustmentItem.objects.filter(item_id=item_id, warehouse=warehouse, adjustment_type='ADD').aggregate(Sum('quantity'))['quantity__sum'] or 0
        decrease_adj_qty = StockAdjustmentItem.objects.filter(item_id=item_id, warehouse=warehouse, adjustment_type='SUB').aggregate(Sum('quantity'))['quantity__sum'] or 0

        current_stock = (opening_stock + inward_qty + produced_qty + transferred_in_qty + increase_adj_qty) - \
                        (outward_qty + consumed_qty + transferred_out_qty + decrease_adj_qty)

        stock_data.append({
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'stock': current_stock,
        })

    return JsonResponse({'stock_data': stock_data})

@login_required
def get_pending_delivery_items_api(request):
    """API to get pending delivery items for a specific person."""
    person_id = request.GET.get('person_id')
    if not person_id:
        return JsonResponse({'error': 'person_id is required'}, status=400)

    pending_items = DeliveryOutItem.objects.filter(
        header__to_person_id=person_id,
        issued_quantity__gt=F('returned_quantity')
    ).values(
        'id', 
        'item__name', 
        'item__code', 
        'from_warehouse__name', 
        'issued_quantity', 
        'returned_quantity'
    )
    
    pending_items_list = list(pending_items)

    for item in pending_items_list:
        item['pending_quantity'] = item['issued_quantity'] - item['returned_quantity']
        item['item_name'] = item.pop('item__name')
        item['item_code'] = item.pop('item__code')
        item['from_warehouse_name'] = item.pop('from_warehouse__name')

    return JsonResponse(pending_items_list, safe=False)
    
@login_required
def get_stock_api(request):
    item_id = request.GET.get('item_id')
    warehouse_id = request.GET.get('warehouse_id')

    if not item_id or not warehouse_id:
        return JsonResponse({'error': 'Item and Warehouse IDs are required.'}, status=400)
    
    # The logic here is similar to the report view but isolated for a single item/warehouse
    opening_stock = OpeningStock.objects.filter(item_id=item_id, warehouse_id=warehouse_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
    inward_qty = InwardItem.objects.filter(item_id=item_id, warehouse_id=warehouse_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
    outward_qty = OutwardItem.objects.filter(item_id=item_id, warehouse_id=warehouse_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
    produced_qty = ProductionItem.objects.filter(item_id=item_id, warehouse_id=warehouse_id, type='Produced').aggregate(Sum('quantity'))['quantity__sum'] or 0
    consumed_qty = ProductionItem.objects.filter(item_id=item_id, warehouse_id=warehouse_id, type='Consumed').aggregate(Sum('quantity'))['quantity__sum'] or 0
    transferred_in_qty = WarehouseTransferItem.objects.filter(item_id=item_id, to_warehouse_id=warehouse_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
    transferred_out_qty = WarehouseTransferItem.objects.filter(item_id=item_id, from_warehouse_id=warehouse_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    increase_adj_qty = StockAdjustmentItem.objects.filter(item_id=item_id, warehouse_id=warehouse_id, adjustment_type='ADD').aggregate(Sum('quantity'))['quantity__sum'] or 0
    decrease_adj_qty = StockAdjustmentItem.objects.filter(item_id=item_id, warehouse_id=warehouse_id, adjustment_type='SUB').aggregate(Sum('quantity'))['quantity__sum'] or 0

    current_stock = (opening_stock + inward_qty + produced_qty + transferred_in_qty + increase_adj_qty) - \
                    (outward_qty + consumed_qty + transferred_out_qty + decrease_adj_qty)
    
    return JsonResponse({'stock': current_stock})


@login_required
def get_pending_items_for_person(request):
    person_id = request.GET.get('person_id')
    
    if not person_id:
        return JsonResponse({'error': 'Person ID is required'}, status=400)

    pending_items = DeliveryOutItem.objects.filter(
        header__to_person_id=person_id,
        issued_quantity__gt=F('returned_quantity')
    ).values(
        'id',
        'item__name',
        'item__code',
        'from_warehouse__name',
        'issued_quantity',
        'returned_quantity'
    ).annotate(pending_quantity=F('issued_quantity') - F('returned_quantity'))
    
    return JsonResponse(list(pending_items), safe=False)

@login_required
def get_alias_data_api(request):
    item_id = request.GET.get('item_id')
    
    if not item_id:
        return JsonResponse({'error': 'Item ID is required'}, status=400)
    
    item = get_object_or_404(ItemMaster, pk=item_id)
    
    aliases = ItemAlias.objects.filter(item=item).values_list('alias_name', flat=True)
    part_numbers = PartNumberAlias.objects.filter(item=item).values_list('alias_part_number', flat=True)
    
    data = {
        'aliases': list(aliases),
        'part_numbers': list(part_numbers),
    }
    
    return JsonResponse(data)

@login_required
def update_multiple_aliases(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        item = get_object_or_404(ItemMaster, pk=item_id)
        
        alias_formset = ItemAliasFormSet(request.POST, request.FILES, instance=item, prefix='aliases')
        part_number_formset = PartNumberAliasFormSet(request.POST, request.FILES, instance=item, prefix='part_numbers')
        
        if alias_formset.is_valid() and part_number_formset.is_valid():
            with transaction.atomic():
                alias_formset.save()
                part_number_formset.save()
            messages.success(request, 'Aliases updated successfully.')
        else:
            messages.error(request, 'Error updating aliases.')
        
    return redirect('item_edit', pk=item_id)