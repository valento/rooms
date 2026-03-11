from fastapi import HTTPException, status

class Permissions:
    """Role-based permission checks."""
    
    ROLE_HIERARCHY = {
        'admin': 4,
        'editor': 3,
        'author': 2,
        'user': 1
    }
    
    @staticmethod
    def require_role(user_role: str, required_role: str) -> bool:
        """Check if user has required role or higher."""
        user_level = Permissions.ROLE_HIERARCHY.get(user_role, 0)
        required_level = Permissions.ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level
    
    @staticmethod
    def check_role(user_role: str, required_role: str):
        """Raise exception if user doesn't have required role."""
        if not Permissions.require_role(user_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher"
            )
    
    @staticmethod
    def can_edit_content(user_id: int, user_role: str, content_author_id: int) -> bool:
        """Check if user can edit specific content."""
        # Admins and editors can edit anything
        if user_role in ['admin', 'editor']:
            return True
        # Authors can only edit their own content
        return user_role == 'author' and user_id == content_author_id