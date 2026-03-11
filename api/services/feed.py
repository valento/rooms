from typing import Optional, List
from models.content import BrickItem, ContentDetail

def build_center_feed(items: List[ContentDetail]) -> List[BrickItem]:
    bricks = []
    remaining = list(items)  # work on a copy
    
    # Build pools by size for companion recruitment
    def pull_first(pool, size):
        """Remove and return first item of given size from remaining."""
        for idx, item in enumerate(pool):
            if (item.widget_size or 'medium') == size:
                return pool.pop(idx)
        return None
    
    i = 0
    while i < len(remaining):
        current = remaining[i]
        size = current.widget_size or 'medium'
        
        if size == 'xlarge':
            bricks.append(BrickItem(brick_type='xlarge', items=[current]))
            remaining.pop(i)
        
        elif size == 'large':
            remaining.pop(i)
            # Try to find a small companion
            companion = pull_first(remaining[i:], 'small')
            if companion:
                bricks.append(BrickItem(brick_type='large_small', items=[current, companion]))
            else:
                # Solo large — no small available
                bricks.append(BrickItem(brick_type='xlarge', items=[current]))
        
        elif size == 'medium':
            remaining.pop(i)
            # Try to pair with next medium
            companion = pull_first(remaining[i:], 'medium')
            if companion:
                bricks.append(BrickItem(brick_type='dual_medium', items=[current, companion]))
            else:
                # Solo medium — render as half-width or upgrade
                bricks.append(BrickItem(brick_type='dual_medium', items=[current]))
        
        elif size == 'small':
            # Collect up to 4 smalls
            group = [current]
            remaining.pop(i)
            while len(group) < 4:
                companion = pull_first(remaining[i:], 'small')
                if companion:
                    group.append(companion)
                else:
                    break
            bricks.append(BrickItem(brick_type='quad_small', items=group))
        
        else:
            bricks.append(BrickItem(brick_type='dual_medium', items=[current]))
            remaining.pop(i)
    
    return bricks