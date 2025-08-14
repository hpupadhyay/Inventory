from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

from .views import (
    # Main
    DashboardView,
    CustomLoginView,
    
    # Master Data
    ItemMasterView, ItemUpdateView, ItemDeleteView,
    update_multiple_aliases,
    GroupMasterView, GroupUpdateView, GroupDeleteView,
    WarehouseMasterView,
    ContactMasterView,
    OpeningStockView, OpeningStockUpdateView, OpeningStockDeleteView,
    
    # Transactions
    InwardView, InwardUpdateView, InwardDeleteView,
    OutwardView, OutwardUpdateView, OutwardDeleteView,
    ProductionView, ProductionUpdateView, ProductionDeleteView,
    WarehouseTransferView, WarehouseTransferUpdateView, WarehouseTransferDeleteView,
    StockAdjustmentView, StockAdjustmentUpdateView, StockAdjustmentDeleteView,
    
    # Delivery Notes
    DeliveryOutView, DeliveryOutUpdateView, DeliveryOutDeleteView,
    DeliveryInView, DeliveryInUpdateView, DeliveryInDeleteView,
    
    # Reports
    StockReportView, StockReportDetailView,
    InwardReportView, OutwardReportView, ProductionReportView,
    WarehouseTransferReportView, DeliveryNoteReportView,
    StockAdjustmentReportView, PendingDeliveryReportView,
    
    # Settings & Management
    BOMView,
    PeriodSettingView,
    UserListView, UserCreateView, UserUpdateView,

    # Import
    ImportView,

    # APIs
    get_items_api,
    get_item_stock_details_api,
    get_pending_delivery_items_api,
    get_stock_api,
    get_pending_items_for_person,
    get_alias_data_api,
    get_item_by_barcode,
    get_pending_delivery_item_details_api,
    get_pending_item_by_barcode_api,
    get_item_details_api
)

urlpatterns = [
    # Authentication
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        success_url='/change-password/done/'
    ), name='password_change'),
    path('change-password/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),

    # Main Page
    path('', DashboardView.as_view(), name='dashboard'),
    
    # Master Data
    path('items/', ItemMasterView.as_view(), name='item_master'),
    path('items/<int:pk>/edit/', ItemUpdateView.as_view(), name='item_edit'),
    path('items/<int:pk>/delete/', ItemDeleteView.as_view(), name='item_delete'),
    
    path('items/update-aliases/', update_multiple_aliases, name='update_multiple_aliases'),
    
    path('groups/', GroupMasterView.as_view(), name='group_master'),
    path('groups/<int:pk>/edit/', GroupUpdateView.as_view(), name='group_edit'),
    path('groups/<int:pk>/delete/', GroupDeleteView.as_view(), name='group_delete'),
    path('warehouses/', WarehouseMasterView.as_view(), name='warehouse_master'),
    path('contacts/', ContactMasterView.as_view(), name='contact_master'),
    path('opening-stock/', OpeningStockView.as_view(), name='opening_stock'),
    path('opening-stock/<int:pk>/edit/', OpeningStockUpdateView.as_view(), name='opening_stock_edit'),
    path('opening-stock/<int:pk>/delete/', OpeningStockDeleteView.as_view(), name='opening_stock_delete'),

    # Transactions
    path('inward/', InwardView.as_view(), name='inward'),
    path('inward/<int:pk>/edit/', InwardUpdateView.as_view(), name='inward_edit'),
    path('inward/<int:pk>/delete/', InwardDeleteView.as_view(), name='inward_delete'),
    path('outward/', OutwardView.as_view(), name='outward'),
    path('outward/<int:pk>/edit/', OutwardUpdateView.as_view(), name='outward_edit'),
    path('outward/<int:pk>/delete/', OutwardDeleteView.as_view(), name='outward_delete'),
    path('production/', ProductionView.as_view(), name='production'),
    path('production/<int:pk>/edit/', ProductionUpdateView.as_view(), name='production_edit'),
    path('production/<int:pk>/delete/', ProductionDeleteView.as_view(), name='production_delete'),
    path('transfer/', WarehouseTransferView.as_view(), name='warehouse_transfer'),
    path('transfer/<int:pk>/edit/', WarehouseTransferUpdateView.as_view(), name='warehouse_transfer_edit'),
    path('transfer/<int:pk>/delete/', WarehouseTransferDeleteView.as_view(), name='warehouse_transfer_delete'),
    path('adjustment/', StockAdjustmentView.as_view(), name='stock_adjustment'),
    path('adjustment/<int:pk>/edit/', StockAdjustmentUpdateView.as_view(), name='stock_adjustment_edit'),
    path('adjustment/<int:pk>/delete/', StockAdjustmentDeleteView.as_view(), name='stock_adjustment_delete'),

    # Delivery Notes
    path('delivery-out/', DeliveryOutView.as_view(), name='delivery_out'),
    path('delivery-out/<int:pk>/edit/', DeliveryOutUpdateView.as_view(), name='delivery_out_edit'),
    path('delivery-out/<int:pk>/delete/', DeliveryOutDeleteView.as_view(), name='delivery_out_delete'),
    path('delivery-in/', DeliveryInView.as_view(), name='delivery_in'),
    path('delivery-in/<int:pk>/edit/', DeliveryInUpdateView.as_view(), name='delivery_in_edit'),
    path('delivery-in/<int:pk>/delete/', DeliveryInDeleteView.as_view(), name='delivery_in_delete'),
    
    # Reports
    path('report/', StockReportView.as_view(), name='stock_report'),
    path('report/detail/', StockReportDetailView.as_view(), name='stock_report_detail'),
    path('report/pending-delivery/', PendingDeliveryReportView.as_view(), name='pending_delivery_report'),
    path('report/inward/', InwardReportView.as_view(), name='inward_report'),
    path('report/outward/', OutwardReportView.as_view(), name='outward_report'),
    path('report/production/', ProductionReportView.as_view(), name='production_report'),
    path('report/transfer/', WarehouseTransferReportView.as_view(), name='warehouse_transfer_report'),
    path('report/adjustment/', StockAdjustmentReportView.as_view(), name='stock_adjustment_report'),
    path('report/delivery-note/', DeliveryNoteReportView.as_view(), name='delivery_note_report'),
    
    # Settings & Management
    path('settings/bom/', BOMView.as_view(), name='bom_create'),
    path('settings/period/', PeriodSettingView.as_view(), name='period_setting'),
    path('manage/users/', UserListView.as_view(), name='user_list'),
    path('manage/users/add/', UserCreateView.as_view(), name='user_create'),
    path('manage/users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    
    # Import
    path('import/', ImportView.as_view(), name='import_page'),
    path('download_template/<str:section_name>/', views.download_template, name='download_template'),

    
    # APIs
    path('api/get-item-details/', views.get_item_details_api, name='get_item_details_api'),
    path('api/get-items/', get_items_api, name='get_items_api'),
    path('api/get-stock/', get_stock_api, name='get_stock_api'),
    path('api/get-item-stock-details/', get_item_stock_details_api, name='get_item_stock_details_api'),
    path('api/get-pending-items/', get_pending_items_for_person, name='get_pending_items'),
    path('api/get-pending-delivery-items/', get_pending_delivery_items_api, name='get_pending_delivery_items_api'),
    path('api/get-pending-delivery-item-details/', views.get_pending_delivery_item_details_api, name='get_pending_delivery_item_details_api'),
    path('api/get-alias-data/', get_alias_data_api, name='get_alias_data_api'),
    path('get_item_by_barcode/', views.get_item_by_barcode, name='get_item_by_barcode'),
    path('api/get-pending-item-by-barcode/', views.get_pending_item_by_barcode_api, name='get_pending_item_by_barcode_api'),
]