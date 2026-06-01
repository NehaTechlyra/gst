#!/usr/bin/env python
"""
Fix for cities_light TEXT index issue on MySQL.
Run this after installing dependencies and before first migration.
"""

import os
import sys

# Ensure Django settings are configured before importing cities_light
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Lyraerp.settings')

def patch_cities_light_migration():
    """Patch the cities_light migration to prevent MySQL index errors."""
    
    # Locate cities_light migrations directory
    try:
        import cities_light
        cities_light_path = os.path.dirname(cities_light.__file__)
        migration_file = os.path.join(
            cities_light_path, 
            'migrations',
            '0013_alter_city_alternate_names_alter_city_country_and_more.py'
        )
        
        if not os.path.exists(migration_file):
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Check if already patched
        if 'db_index=False' in content and 'search_names' in content:
            print("✅ cities_light migration already patched")
            return True
        
        # Apply patch
        if 'db_index=True' in content and 'search_names' in content:
            patched_content = content.replace(
                '''migrations.AlterField(
            model_name="city",
            name="search_names",
            field=cities_light.abstract_models.ToSearchTextField(
                blank=True,
                db_index=True,
                default="",
                max_length=4000,
                verbose_name="search names",
            ),
        ),''',
                '''migrations.AlterField(
            model_name="city",
            name="search_names",
            field=cities_light.abstract_models.ToSearchTextField(
                blank=True,
                db_index=False,
                default="",
                max_length=4000,
                verbose_name="search names",
            ),
        ),'''
            )
            
            with open(migration_file, 'w') as f:
                f.write(patched_content)
            
            print("✅ Successfully patched cities_light migration (db_index=False)")
            return True
        
    except Exception as e:
        print(f"❌ Error patching cities_light: {e}")
        return False

if __name__ == '__main__':
    success = patch_cities_light_migration()
    sys.exit(0 if success else 1)
