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


@receiver(post_save, sender='company.Company')
def create_default_warehouse_signal(sender, instance, created, update_fields=None, **kwargs):
    """
    Signal to create a default warehouse when a company's db_created flag is set to True.
    
    This handles the case where db_created is updated via update_fields (most common in the
    first login flow).
    """
    
    # Check if this is an update to db_created field
    if update_fields and 'db_created' in update_fields and instance.db_created:
        logger.debug(
            f"[WAREHOUSE SIGNAL] db_created set to True for company '{instance.name}', creating warehouse..."
        )
        create_default_warehouse_for_company(instance)