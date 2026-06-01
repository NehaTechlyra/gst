"""
DEBUGGING SCRIPT - Multi-Tenant Login Issues
Run this in Django shell: python manage.py shell
"""

from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.hashers import make_password, check_password
from user.models import User as CustomUser, Role
from company.models import Company
from django.db import connections

def debug_user_login(username_or_email, password):
    """Debug why a user can't login"""
    
    print("\n" + "="*80)
    print("🔍 DEBUGGING LOGIN ISSUE")
    print("="*80)
    
    # Step 1: Check if user exists in master database
    print(f"\n1️⃣ Checking MASTER database for: {username_or_email}")
    print("-" * 80)
    
    # Try by username
    custom_user = CustomUser.objects.using('default').filter(
        usr_name=username_or_email
    ).first()
    
    if not custom_user:
        # Try by email
        custom_user = CustomUser.objects.using('default').filter(
            usr_mail=username_or_email
        ).first()
    
    if not custom_user:
        print(f"❌ USER NOT FOUND in master database!")
        print(f"   Searched for: {username_or_email}")
        
        # Show all users in master
        print("\n📋 All users in MASTER database:")
        all_users = CustomUser.objects.using('default').all()
        for u in all_users:
            print(f"   - usr_name: {u.usr_name}, usr_mail: {u.usr_mail}")
        
        return
    
    print(f"✅ USER FOUND in master database:")
    print(f"   ID: {custom_user.id}")
    print(f"   usr_name: {custom_user.usr_name}")
    print(f"   usr_mail: {custom_user.usr_mail}")
    print(f"   usr_fname: {custom_user.usr_fname}")
    print(f"   usr_roleid: {custom_user.usr_roleid_id}")
    
    # Step 2: Check password
    print(f"\n2️⃣ Checking PASSWORD")
    print("-" * 80)
    
    print(f"   Stored password hash: {custom_user.usr_pwd[:50]}...")
    print(f"   Provided password: {password}")
    
    is_valid = check_password(password, custom_user.usr_pwd)
    
    if is_valid:
        print(f"✅ PASSWORD MATCHES!")
    else:
        print(f"❌ PASSWORD DOES NOT MATCH!")
        print(f"   This means either:")
        print(f"   - Wrong password entered")
        print(f"   - Password not hashed correctly in database")
        
        # Try to check if password is stored as plain text
        if custom_user.usr_pwd == password:
            print(f"   ⚠️  PASSWORD IS STORED AS PLAIN TEXT! This is a security issue.")
            print(f"   Fix by running: user.usr_pwd = make_password('{password}')")
    
    # Step 3: Check role and company
    print(f"\n3️⃣ Checking ROLE & COMPANY")
    print("-" * 80)
    
    if not custom_user.usr_roleid:
        print(f"❌ USER HAS NO ROLE ASSIGNED!")
        return
    
    role = custom_user.usr_roleid
    print(f"✅ ROLE FOUND:")
    print(f"   Role ID: {role.id}")
    print(f"   Role Name: {role.role_name}")
    print(f"   Company ID: {role.company_id}")
    
    if not role.company:
        print(f"❌ ROLE HAS NO COMPANY ASSIGNED!")
        return
    
    company = role.company
    print(f"✅ COMPANY FOUND:")
    print(f"   Company ID: {company.id}")
    print(f"   Company Name: {company.name}")
    print(f"   Company DB: {company.db_name}")
    print(f"   Setup Complete: {company.setup_complete}")
    
    # Step 4: Check if company database exists
    print(f"\n4️⃣ Checking COMPANY DATABASE")
    print("-" * 80)
    
    db_name = company.db_name
    
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
            result = cursor.fetchone()
            
            if result:
                print(f"✅ DATABASE EXISTS: {db_name}")
                
                # Check if user exists in company database
                try:
                    from Lyraerp.utils.db_utils import register_database
                    register_database(db_name)
                    
                    company_user = CustomUser.objects.using(db_name).filter(
                        usr_name=custom_user.usr_name
                    ).first()
                    
                    if company_user:
                        print(f"✅ USER EXISTS in company database:")
                        print(f"   ID: {company_user.id}")
                        print(f"   usr_name: {company_user.usr_name}")
                        print(f"   company_id: {company_user.company_id}")
                    else:
                        print(f"❌ USER DOES NOT EXIST in company database!")
                        print(f"   This might cause issues if app expects user in company DB")
                        
                except Exception as e:
                    print(f"⚠️  Error checking company database: {e}")
                    
            else:
                print(f"❌ DATABASE DOES NOT EXIST: {db_name}")
                
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    # Step 5: Check Django auth user
    print(f"\n5️⃣ Checking DJANGO AUTH USER (auth_user table)")
    print("-" * 80)
    
    django_user = DjangoUser.objects.using('default').filter(
        username=custom_user.usr_name
    ).first()
    
    if django_user:
        print(f"✅ DJANGO USER EXISTS:")
        print(f"   ID: {django_user.id}")
        print(f"   Username: {django_user.username}")
        print(f"   Email: {django_user.email}")
        print(f"   Is Active: {django_user.is_active}")
    else:
        print(f"⚠️  DJANGO USER DOES NOT EXIST")
        print(f"   This is OK - it will be created during login")
    
    # Summary
    print(f"\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    if is_valid and role and company:
        print(f"✅ User should be able to login!")
        print(f"   Username: {custom_user.usr_name}")
        print(f"   OR Email: {custom_user.usr_mail}")
        print(f"   Company: {company.name}")
        print(f"   Database: {company.db_name}")
    else:
        print(f"❌ User CANNOT login due to:")
        if not is_valid:
            print(f"   - Password mismatch")
        if not role:
            print(f"   - No role assigned")
        if not company:
            print(f"   - No company assigned")
    
    print("="*80 + "\n")


def check_super_admin():
    """Check super admin configuration"""
    
    print("\n" + "="*80)
    print("🔍 CHECKING SUPER ADMIN")
    print("="*80)
    
    # Check in master database
    print(f"\n1️⃣ Checking MASTER database")
    print("-" * 80)
    
    django_sa = DjangoUser.objects.using('default').filter(username='suadmin').first()
    custom_sa = CustomUser.objects.using('default').filter(usr_name='suadmin').first()
    
    if django_sa:
        print(f"✅ Super admin in Django auth_user:")
        print(f"   ID: {django_sa.id}")
        print(f"   Is Superuser: {django_sa.is_superuser}")
        print(f"   Is Staff: {django_sa.is_staff}")
    else:
        print(f"❌ Super admin NOT in Django auth_user")
    
    if custom_sa:
        print(f"✅ Super admin in CustomUser:")
        print(f"   ID: {custom_sa.id}")
        print(f"   usr_name: {custom_sa.usr_name}")
        print(f"   Role: {custom_sa.usr_roleid_id}")
    else:
        print(f"⚠️  Super admin NOT in CustomUser (this is OK)")
    
    # Check all company databases
    print(f"\n2️⃣ Checking COMPANY databases")
    print("-" * 80)
    
    companies = Company.objects.using('default').all()
    
    if not companies:
        print(f"⚠️  No companies found in database")
        return
    
    for company in companies:
        print(f"\n   Company: {company.name} ({company.db_name})")
        
        if not company.db_name:
            print(f"   ❌ No database name set")
            continue
        
        try:
            # Check if database exists
            with connections['default'].cursor() as cursor:
                cursor.execute(f"SHOW DATABASES LIKE '{company.db_name}'")
                result = cursor.fetchone()
                
                if not result:
                    print(f"   ❌ Database does not exist: {company.db_name}")
                    continue
                
            print(f"   ✅ Database exists")
            
            # Register and check for super admin
            from Lyraerp.utils.db_utils import register_database
            register_database(company.db_name)
            
            # Check CustomUser table
            company_sa = CustomUser.objects.using(company.db_name).filter(
                usr_name='suadmin'
            ).first()
            
            if company_sa:
                print(f"   ✅ Super admin exists in CustomUser table")
                print(f"      ID: {company_sa.id}")
            else:
                print(f"   ❌ Super admin NOT in CustomUser table")
                
            # Check Django auth_user table
            django_sa_company = DjangoUser.objects.using(company.db_name).filter(
                username='suadmin'
            ).first()
            
            if django_sa_company:
                print(f"   ✅ Super admin exists in auth_user table")
            else:
                print(f"   ❌ Super admin NOT in auth_user table")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("="*80 + "\n")


def fix_password(username, new_password):
    """Fix a user's password if it's stored incorrectly"""
    
    print(f"\n🔧 Fixing password for: {username}")
    
    custom_user = CustomUser.objects.using('default').filter(usr_name=username).first()
    
    if not custom_user:
        print(f"❌ User not found: {username}")
        return
    
    # Hash the password
    hashed_password = make_password(new_password)
    custom_user.usr_pwd = hashed_password
    custom_user.save(using='default')
    
    print(f"✅ Password updated in MASTER database")
    
    # Update in company database if exists
    if custom_user.usr_roleid and custom_user.usr_roleid.company:
        company = custom_user.usr_roleid.company
        if company.db_name:
            try:
                from Lyraerp.utils.db_utils import register_database
                register_database(company.db_name)
                
                company_user = CustomUser.objects.using(company.db_name).filter(
                    usr_name=username
                ).first()
                
                if company_user:
                    company_user.usr_pwd = hashed_password
                    company_user.save(using=company.db_name)
                    print(f"✅ Password updated in COMPANY database: {company.db_name}")
                else:
                    print(f"⚠️  User not found in company database")
                    
            except Exception as e:
                print(f"❌ Error updating company database: {e}")
    
    print(f"✅ Password fix complete!")


def show_all_users():
    """Show all users in master database"""
    
    print("\n" + "="*80)
    print("📋 ALL USERS IN MASTER DATABASE")
    print("="*80 + "\n")
    
    users = CustomUser.objects.using('default').select_related(
        'usr_roleid__company'
    ).all()
    
    if not users:
        print("No users found!")
        return
    
    for user in users:
        print(f"User ID: {user.id}")
        print(f"  usr_name: {user.usr_name}")
        print(f"  usr_mail: {user.usr_mail}")
        print(f"  usr_fname: {user.usr_fname}")
        
        if user.usr_roleid:
            print(f"  Role: {user.usr_roleid.role_name} (ID: {user.usr_roleid.id})")
            if user.usr_roleid.company:
                print(f"  Company: {user.usr_roleid.company.name} (DB: {user.usr_roleid.company.db_name})")
            else:
                print(f"  Company: None")
        else:
            print(f"  Role: None")
        
        # Check password format
        if user.usr_pwd.startswith('pbkdf2_sha256$') or user.usr_pwd.startswith('bcrypt$'):
            print(f"  Password: ✅ Properly hashed")
        else:
            print(f"  Password: ⚠️  May not be hashed correctly")
        
        print("-" * 80)
    
    print("\n")


# Usage examples
print("""
HOW TO USE THIS DEBUGGING SCRIPT:

1. Show all users:
   >>> show_all_users()

2. Debug a specific user login:
   >>> debug_user_login('username_or_email', 'password')
   
   Example:
   >>> debug_user_login('john', 'mypassword123')
   >>> debug_user_login('john@example.com', 'mypassword123')

3. Check super admin configuration:
   >>> check_super_admin()

4. Fix a user's password:
   >>> fix_password('username', 'new_password')
   
   Example:
   >>> fix_password('john', 'mypassword123')

5. For your specific issue, run:
   >>> show_all_users()  # See all users first
   >>> debug_user_login('your_username', 'your_password')  # Debug login
   >>> check_super_admin()  # Check super admin setup
""")