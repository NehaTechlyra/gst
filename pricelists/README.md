# 📋 Price List Module for Django ERP
Inspired by Zoho Books Price Lists — full CRUD, AJAX item management, CSV export.

---

## 📁 File Structure

```
pricelists/
├── __init__.py
├── models.py              ← DB schema (3 models)
├── views.py               ← All views + AJAX APIs
├── forms.py               ← Django forms with validation
├── urls.py                ← URL routing
├── admin.py               ← Django admin config
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py    ← DB migration
└── templates/pricelists/
    ├── base.html           ← Sidebar layout + full CSS
    ├── index.html          ← Price list listing page
    ├── detail.html         ← Detail + item management
    ├── form.html           ← Create / Edit form
    └── confirm_delete.html ← Delete confirmation
```

---

## ⚡ Integration Steps

### 1. Copy the app into your Django project
```bash
cp -r pricelists/ your_project/
```

### 2. Add to INSTALLED_APPS in settings.py
```python
INSTALLED_APPS = [
    ...
    'pricelists',
]
```

### 3. Include URLs in your main urls.py
```python
# your_project/urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('pricelists/', include('pricelists.urls')),
]
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. (Optional) Configure TEMPLATES in settings.py
Make sure Django can find the templates. In settings.py:
```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],          # or your custom template dirs
        'APP_DIRS': True,    # this auto-discovers app templates/
        ...
    }
]
```

---

## 🗄️ Database Tables

| Table | Purpose |
|---|---|
| `erp_price_lists` | Main price list records |
| `erp_price_list_items` | Items with pricing inside each list |
| `erp_contact_price_lists` | Assigns price lists to customers/vendors |

---

## 🔗 Available URLs

| URL | Name | Description |
|---|---|---|
| `/pricelists/` | `pricelists:index` | List all price lists |
| `/pricelists/create/` | `pricelists:create` | Create new price list |
| `/pricelists/<pk>/` | `pricelists:detail` | View + manage items |
| `/pricelists/<pk>/edit/` | `pricelists:edit` | Edit price list |
| `/pricelists/<pk>/delete/` | `pricelists:delete` | Delete price list |
| `/pricelists/<pk>/toggle-status/` | `pricelists:toggle_status` | AJAX toggle active |
| `/pricelists/<pk>/duplicate/` | `pricelists:duplicate` | Duplicate price list |
| `/pricelists/<pk>/export-csv/` | `pricelists:export_csv` | Download CSV |
| `/pricelists/<pk>/items/create/` | `pricelists:item_create` | AJAX add item |
| `/pricelists/items/<pk>/update/` | `pricelists:item_update` | AJAX edit item |
| `/pricelists/items/<pk>/delete/` | `pricelists:item_delete` | AJAX delete item |
| `/pricelists/api/item-price/` | `pricelists:get_item_price` | Get item price by SKU |

---

## 💡 Using the Price API in Transactions

When creating invoices or sales orders, fetch the price from a price list:

```javascript
// In your invoice JS — get price when item/pricelist changes
fetch(`/pricelists/api/item-price/?price_list_id=3&item_sku=SKU-001`)
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      document.getElementById('unit-price').value = data.final_price;
    }
  });
```

Or in Python/Django views:
```python
from pricelists.models import PriceListItem

def get_price(price_list_id, item_sku):
    try:
        item = PriceListItem.objects.get(price_list_id=price_list_id, item_sku=item_sku)
        return item.final_price
    except PriceListItem.DoesNotExist:
        return None
```

---

## ✨ Features (Zoho Books Parity)

- ✅ Sales & Purchase price lists
- ✅ Percentage, Fixed, and Custom pricing
- ✅ Active/Inactive toggle (click badge)
- ✅ Validity dates (valid_from / valid_to)
- ✅ Duplicate a price list with all items
- ✅ CSV export of all items
- ✅ AJAX add/edit/delete items (no page reload)
- ✅ Search & filter on listing page
- ✅ Contact assignment model (ContactPriceList)
- ✅ Admin panel integration
- ✅ API endpoint for use in transactions
- ✅ Full form validation
