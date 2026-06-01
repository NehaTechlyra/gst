from django.db import migrations
import csv
from pathlib import Path

def insert_hsn_codes_from_csv(apps, schema_editor):
    """Insert all HSN codes from the attached CSV file into Items app"""
    HSNCode = apps.get_model('Items', 'HSNCode')
    db = schema_editor.connection.alias  # Get the current database being migrated
    
    # Since this is a migration, read from file system
    # Place item_hsncode.csv in the same directory as this migration file
    csv_path = Path(__file__).parent / 'item_hsncode.csv'
    
    if not csv_path.exists():
        print("WARNING: item_hsncode.csv not found in migrations folder.")
        print("Please copy the CSV file to: ", csv_path)
        return
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    print("Starting HSN code import...")
    
    with csv_path.open('r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        
        for row_num, row in enumerate(reader, start=1):
            try:
                # Clean code and description from quotes and whitespace
                code = row['code'].strip().strip('"')
                description = row['description'].strip().strip('"')
                
                # Validate HSN code format (4, 6, or 8 digits typically)
                if len(code) > 10 or not code.replace('-', '').isdigit():
                    print(f"Row {row_num}: Invalid code format: '{code}'")
                    error_count += 1
                    continue
                
                # Skip if already exists (unique constraint on code)
                if HSNCode.objects.using(db).filter(code=code).exists():
                    skipped_count += 1
                    continue
                
                # Create HSN code record
                HSNCode.objects.using(db).create(
                    code=code,
                    description=description
                )
                created_count += 1
                
                # Progress indicator
                if row_num % 1000 == 0:
                    print(f"Progress: {row_num:,} rows | Created: {created_count:,} | Skipped: {skipped_count:,} | Errors: {error_count:,}")
                    
            except KeyError as e:
                print(f"Row {row_num}: Missing column {e}")
                error_count += 1
            except Exception as e:
                print(f"Row {row_num}: Error - {str(e)[:100]}")
                error_count += 1
                continue
    
    print(f"\n✅ Migration COMPLETE!")
    print(f"   Created: {created_count:,} new HSN codes")
    print(f"   Skipped: {skipped_count:,} duplicates") 
    print(f"   Errors:  {error_count:,} invalid rows")
    print(f"   Total processed: {created_count + skipped_count + error_count:,}")

def reverse_hsn_codes(apps, schema_editor):
    """Reverse migration - delete ALL HSN codes (use with caution!)"""
    HSNCode = apps.get_model('Items', 'HSNCode')
    db = schema_editor.connection.alias
    deleted_count, _ = HSNCode.objects.using(db).all().delete()
    print(f"🔄 Reversed: Deleted {deleted_count} HSN codes")

class Migration(migrations.Migration):

    dependencies = [
        ('Items', '0002_initial'),  # Adjust to your last Items migration
    ]

    operations = [
        migrations.RunPython(insert_hsn_codes_from_csv, reverse_hsn_codes),
    ]
