from typing import Optional, List
from models.content import BrickItem, ContentDetail

def build_feed(items: List[ContentDetail]) -> List[BrickItem]:
    bricks = []
    remaining = list(items)
    
    def pull_first(size, start_idx=0):
        """Remove and return first item of given size from remaining."""
        for idx in range(start_idx, len(remaining)):
            if (remaining[idx].widget_size or 'medium') == size:
                return remaining.pop(idx)
        return None
    
    while remaining:
        current = remaining.pop(0)
        size = current.widget_size or 'medium'
        
        if size == 'xlarge':
            bricks.append(BrickItem(brick_type='xlarge', items=[current]))
        
        elif size == 'large':
            companion = pull_first('small')
            if companion:
                bricks.append(BrickItem(brick_type='large_small', items=[current, companion]))
            else:
                bricks.append(BrickItem(brick_type='xlarge', items=[current]))
        
        elif size == 'medium':
            companion = pull_first('medium')
            if companion:
                bricks.append(BrickItem(brick_type='dual_medium', items=[current, companion]))
            else:
                bricks.append(BrickItem(brick_type='dual_medium', items=[current]))
        
        elif size == 'small':
            group = [current]
            while len(group) < 4:
                companion = pull_first('small')
                if companion:
                    group.append(companion)
                else:
                    break
            bricks.append(BrickItem(brick_type='quad_small', items=group))
        
        else:
            bricks.append(BrickItem(brick_type='dual_medium', items=[current]))
    
    return bricks