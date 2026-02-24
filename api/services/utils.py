# services/utils.py (or similar)
from slugify import slugify
from services.database import execute_query

def generate_unique_slug(title: str, existing_id: int = None) -> str:
    """Generate unique slug from title."""
    base_slug = slugify(title, max_length=240)
    slug = base_slug
    counter = 1
    
    while True:
        # Check if slug exists (exclude current record on update)
        if existing_id:
            sql = "SELECT id FROM company.content_blocks WHERE slug = %s AND id != %s"
            result = execute_query(sql, (slug, existing_id))
        else:
            sql = "SELECT id FROM company.content_blocks WHERE slug = %s"
            result = execute_query(sql, (slug,))
        
        if not result:
            return slug
        
        # Slug exists, add counter
        slug = f"{base_slug}-{counter}"
        counter += 1