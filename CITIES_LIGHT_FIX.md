# Installation Guide - MySQL cities_light Migration Fix

## Issue
The `cities_light` package has a known issue with MySQL where migration `0013_alter_city_alternate_names_alter_city_country_and_more` attempts to create an index on a TEXT field (`search_names`) without specifying a key length. MySQL doesn't allow this.

**Error:**
```
MySQLdb.OperationalError: (1170, "BLOB/TEXT column 'search_names' used in key specification without a key length")
```

## Solution - Choose One:

### **Method 1: Automatic Patch (Recommended)**
Run the patch script before migrations:

```powershell
python patch_cities_light.py
python manage.py migrate --database=default
```

### **Method 2: Manual Fix**
Edit the cities_light migration directly:

**File:** `C:\Users\{USERNAME}\AppData\Roaming\Python\Python313\site-packages\cities_light\migrations\0013_alter_city_alternate_names_alter_city_country_and_more.py`

**Change line ~103 from:**
```python
db_index=True,
```

**To:**
```python
db_index=False,
```

### **Method 3: Use Environment Variable**
In your project settings, ensure you have:

```python
# settings.py
CITIES_LIGHT_INDEX_SEARCH_NAMES = False
```

This is already in the project but doesn't prevent the migration from trying to index the field.

## Prevention Checklist

When setting up a fresh installation:

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run patch: `python patch_cities_light.py`
- [ ] Run migrations: `python manage.py migrate --database=default`
- [ ] Verify no errors in migration output

## Why This Happens

The cities_light package was updated with a migration that doesn't account for MySQL's requirement of specifying key length for TEXT/BLOB columns. Setting `db_index=False` prevents the index creation since the `CITIES_LIGHT_INDEX_SEARCH_NAMES` setting is already False.

## For Future Versions

Monitor the [cities-light GitHub repository](https://github.com/coderholic/django-cities-light) for updates that may fix this issue upstream.
