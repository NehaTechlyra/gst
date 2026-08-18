from rest_framework import serializers
from django.db import models, transaction

from .models import DeliveryNote,DeliveryNoteItem,StockMovement
from company.utils import is_stock_management_on_delivery

class DeliveryNoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='bill_item.product.name', read_only=True)
    ordered_quantity = serializers.IntegerField(source='bill_item.quantity', read_only=True)
    already_delivered = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryNoteItem
        fields = ['id', 'bill_item', 'product_name', 'ordered_quantity', 
                  'quantity_delivered', 'already_delivered', 'remaining_quantity', 'notes']
    
    def get_already_delivered(self, obj):
        return DeliveryNoteItem.objects.filter(
            bill_item=obj.bill_item,
            delivery_note__stock_updated=True
        ).exclude(pk=obj.pk).aggregate(
            total=models.Sum('quantity_delivered')
        )['total'] or 0
    
    def get_remaining_quantity(self, obj):
        already_delivered = self.get_already_delivered(obj)
        return obj.bill_item.quantity - already_delivered - obj.quantity_delivered
    
    def validate(self, data):
        bill_item = data.get('bill_item')
        quantity_delivered = data.get('quantity_delivered')
        
        # Get total already delivered (only count delivered items)
        total_delivered = DeliveryNoteItem.objects.filter(
            bill_item=bill_item,
            delivery_note__stock_updated=True
        ).exclude(pk=self.instance.pk if self.instance else None).aggregate(
            total=models.Sum('quantity_delivered')
        )['total'] or 0
        
        if (total_delivered + quantity_delivered) > bill_item.quantity:
            raise serializers.ValidationError(
                f"Total delivered quantity ({total_delivered + quantity_delivered}) "
                f"exceeds ordered quantity ({bill_item.quantity})"
            )
        
        return data


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='stock.item.name', read_only=True)
    warehouse_name = serializers.CharField(source='stock.warehouse.warehouse_name', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = ['id', 'stock', 'item_name', 'warehouse_name', 'movement_type', 
                  'quantity', 'reference_type', 'reference_id', 'notes', 'created_at']
        read_only_fields = ['created_at']


class DeliveryNoteSerializer(serializers.ModelSerializer):
    items = DeliveryNoteItemSerializer(many=True)
    bill_number = serializers.CharField(source='bill.bill_number', read_only=True)
    vendor_name = serializers.CharField(source='bill.vendor.first_name', read_only=True)
    warehouse_name = serializers.CharField(source='bill.warehouse.warehouse_name', read_only=True)
    stock_movements = StockMovementSerializer(many=True, read_only=True)
    
    class Meta:
        model = DeliveryNote
        fields = ['id', 'bill', 'bill_number', 'vendor_name', 'warehouse_name',
                  'delivery_note_number', 'delivery_date', 'received_by', 'notes', 
                  'status', 'stock_updated', 'items', 'stock_movements',
                  'created_at', 'updated_at']
        read_only_fields = ['delivery_note_number', 'stock_updated', 'created_at', 'updated_at']

    def _is_delivery_stock_enabled(self):
        request = self.context.get('request') if hasattr(self, 'context') else None
        return is_stock_management_on_delivery(request=request)
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        delivery_note = DeliveryNote.objects.create(**validated_data)
        
        for item_data in items_data:
            DeliveryNoteItem.objects.create(delivery_note=delivery_note, **item_data)
        
        # Auto-update stock only when the company setting is delivery-based.
        if delivery_note.status == 'delivered' and self._is_delivery_stock_enabled():
            delivery_note.update_stock()
        
        return delivery_note
    
    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        old_status = instance.status
        
        # Update delivery note fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            # Only allow item updates if stock hasn't been updated
            if instance.stock_updated:
                raise serializers.ValidationError(
                    "Cannot modify items after stock has been updated. "
                    "Please cancel the delivery note first."
                )
            
            instance.items.all().delete()
            for item_data in items_data:
                DeliveryNoteItem.objects.create(delivery_note=instance, **item_data)
        
        # Handle stock updates based on status change
        if instance.status == 'delivered' and old_status != 'delivered' and self._is_delivery_stock_enabled():
            instance.update_stock()
        elif instance.status == 'cancelled' and old_status != 'cancelled':
            instance.reverse_stock()
        
        return instance
