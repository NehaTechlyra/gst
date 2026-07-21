import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

logger = logging.getLogger(__name__)


def create_default_warehouse_for_company(company):
    """
    Helper function to create a default warehouse in a company's database.
    
    Args:
        company: Company instance with db_name and db_created set
        
    Returns:
        True if warehouse was created, False otherwise
    """
    
    if not company.db_name or not company.db_created:
        logger.debug(
            f"[WAREHOUSE] Skipping warehouse creation for '{company.name}' — "
            f"db_name={company.db_name}, db_created={company.db_created}"
        )
        return False
    
    try:
        from Lyraerp.utils.db_utils import register_database
        from warehouse.models import Warehouse
        
        # Register and use the company's database
        register_database(company.db_name)
        
        # Check if default warehouse already exists
        existing = Warehouse.objects.using(company.db_name).filter(is_default=True).exists()
        if existing:
            logger.info(
                f"[WAREHOUSE] Default warehouse already exists for company '{company.name}'"
            )
            return False
        
        # Build the warehouse address from company address fields
        address_parts = []
        if company.address_line1:
            address_parts.append(company.address_line1)
        if company.address_line2:
            address_parts.append(company.address_line2)
        if company.city:
            address_parts.append(company.city)
        if company.state:
            address_parts.append(company.state)
        if company.postal_code:
            address_parts.append(company.postal_code)
        if company.country:
            address_parts.append(str(company.country))
        
        warehouse_address = ", ".join(address_parts) if address_parts else "Address not provided"
        
        # Create default warehouse in company database
        warehouse_code = f"{company.company_code}-DEFAULT" if company.company_code else "DEFAULT-WH"
        
        warehouse = Warehouse(
            warehouse_name=f"{company.name} - Default Warehouse",
            code=warehouse_code,
            address=warehouse_address,
            status=True,
            is_default=True,
            description=f"Default warehouse for {company.name}"
        )
        
        warehouse.save(using=company.db_name)
        
        logger.info(
            f"[WAREHOUSE] Created default warehouse '{warehouse.warehouse_name}' "
            f"for company '{company.name}' in database '{company.db_name}'"
        )
        return True
        
    except Exception as e:
        logger.error(
            f"[WAREHOUSE] Failed to create default warehouse for company '{company.name}': {str(e)}",
            exc_info=True
        )
        return False
def create_default_cash_customer_for_company(company):
    """
    Helper function to create a default "cash customer" in a company's database.
    
    Args:
        company: Company instance with db_name and db_created set
        
    Returns:
        True if customer was created, False otherwise
    """
    
    if not company.db_name or not company.db_created:
        logger.debug(
            f"[CASH CUSTOMER] Skipping customer creation for '{company.name}' — "
            f"db_name={company.db_name}, db_created={company.db_created}"
        )
        return False
    
    try:
        from Lyraerp.utils.db_utils import register_database
        from customer.models import Customer
        
        # Register and use the company's database
        register_database(company.db_name)
        
        # Check if cash customer already exists
        existing = Customer.objects.using(company.db_name).filter(
            customer_code__iexact='CASH'
        ).exists()
        if existing:
            logger.info(
                f"[CASH CUSTOMER] Cash customer already exists for company '{company.name}'"
            )
            return False
        
        # Use company address for cash customer
        address_line_1 = "N/A"
        address_line_2 = "N/A"
        city = "N/A"
        state = "N/A"
        postal_code = "N/A"
        country = company.country or ""
        
        # Create default cash customer in company database
        customer = Customer(
            customer_code="CASH",
            customer_type="individual",
            first_name="Cash",
            last_name="Customer",
            email=f"N/A",
            phone="",
            mobile="",
            is_draft=False,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            shipping_address_line_1=address_line_1,
            shipping_address_line_2=address_line_2,
            shipping_city=city,
            shipping_state=state,
            shipping_postal_code=postal_code,
            shipping_country=country,
            tax_preference="taxable",
            currency=getattr(company, 'base_currency', 'INR') or 'INR',
            opening_balance=0,
            is_active=True,
            is_vendor=False,
        )
        
        customer.save(using=company.db_name)
        
        logger.info(
            f"[CASH CUSTOMER] Created default 'Cash Customer' "
            f"for company '{company.name}' in database '{company.db_name}'"
        )
        return True
        
    except Exception as e:
        logger.error(
            f"[CASH CUSTOMER] Failed to create default cash customer for company '{company.name}': {str(e)}",
            exc_info=True
        )
        return False


@receiver(post_save, sender='company.Company')
def create_default_warehouse_signal(sender, instance, created, update_fields=None, **kwargs):
    """
    Signal to create a default warehouse and cash customer when a company's db_created flag is set to True.    
    This handles the case where db_created is updated via update_fields (most common in the
    first login flow).
    """
    
    # Check if this is an update to db_created field
    if update_fields and 'db_created' in update_fields and instance.db_created:
        logger.debug(
            f"[DEFAULT SETUP] db_created set to True for company '{instance.name}', creating defaults..."
        )
        create_default_warehouse_for_company(instance)
        create_default_cash_customer_for_company(instance)