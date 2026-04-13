import json
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from models.polls import PollCreate, PollDetail, PollOptionResult, VoteRequest, PollCreated
from services.utils import generate_unique_slug
from services.database import execute_query, get_db_connection
from routers.auth import get_current_user_id

router = APIRouter(prefix="/polls", tags=["polls"])

BINARY_OPTIONS = ["Yes", "No"]
POLL_STATUS_MAP = {
    'draft': 'draft',
    'published': 'active',
}

@router.get("/by-content/{slug}", response_model=PollDetail)
async def get_poll_by_content_slug(slug: str, user_id: Optional[int] = None):
    """Get poll by its content_block slug."""
    
    # 1. Resolve content_block slug → poll_id
    result = execute_query("""
        SELECT p.id AS poll_id
        FROM polls.polls p
        JOIN company.content_blocks cb ON cb.id = p.content_id
        WHERE cb.slug = %s
    """, (slug,))

    if not result:
        raise HTTPException(status_code=404, detail="Poll not found for this slug")

    poll_id = result[0]['poll_id']

    # 2. Reuse existing get_poll()
    return await get_poll(poll_id, user_id)

@router.get("/{poll_id}", response_model=PollDetail)
async def get_poll(poll_id: int, user_id: Optional[int] = None):
    # 1. Fetch poll
    poll_result = execute_query("""
        SELECT p.id, p.content_id, p.question, p.poll_type, 
              p.status, p.closes_at, p.created_at,
              cb.category_id,
              cat.slug AS category_slug
        FROM polls.polls p
        LEFT JOIN company.content_blocks cb ON cb.id = p.content_id
        LEFT JOIN company.categories cat ON cat.id = cb.category_id
        WHERE p.id = %s
    """, (poll_id,))

    if not poll_result:
        raise HTTPException(status_code=404, detail="Poll not found")

    poll = poll_result[0]

    # 2. Fetch options with vote counts
    options_result = execute_query("""
        SELECT 
            o.id, o.text, o.sequence_order,
            COUNT(v.id) AS vote_count
        FROM polls.poll_options o
        LEFT JOIN polls.poll_votes v ON v.option_id = o.id
        WHERE o.poll_id = %s
        GROUP BY o.id, o.text, o.sequence_order
        ORDER BY o.sequence_order
    """, (poll_id,))

    total_votes = sum(r['vote_count'] for r in options_result) if options_result else 0

    # For rating polls total_votes comes from votes table directly
    if poll['poll_type'] == 'rating':
        rating_result = execute_query("""
            SELECT COUNT(*) AS total FROM polls.poll_votes WHERE poll_id = %s
        """, (poll_id,))
        total_votes = rating_result[0]['total'] if rating_result else 0

    options = [
        PollOptionResult(
            id=r['id'],
            text=r['text'],
            sequence_order=r['sequence_order'],
            vote_count=r['vote_count']
        )
        for r in (options_result or [])
    ]

    # 3. Check if this user already voted
    user_voted = False
    user_option_id = None
    if user_id:
        vote_result = execute_query("""
            SELECT option_id FROM polls.poll_votes
            WHERE poll_id = %s AND user_id = %s
        """, (poll_id, user_id))
        if vote_result:
            user_voted = True
            user_option_id = vote_result[0]['option_id']

    return PollDetail(
        **poll,
        options=options,
        total_votes=total_votes,
        user_voted=user_voted,
        user_option_id=user_option_id
    )

@router.post("/{poll_id}/vote", response_model=PollDetail)
async def submit_vote(poll_id: int,
    vote: VoteRequest,
    user_id: int = Depends(get_current_user_id)):
    # 1. Check poll exists and is active
    poll_result = execute_query("""
        SELECT id, poll_type, status, closes_at
        FROM polls.polls
        WHERE id = %s
    """, (poll_id,))

    if not poll_result:
        raise HTTPException(status_code=404, detail="Poll not found")

    poll = poll_result[0]

    if poll['status'] != 'active':
        raise HTTPException(status_code=400, detail="Poll is not active")

    # 2. Check user hasn't already voted
    existing = execute_query("""
        SELECT id FROM polls.poll_votes
        WHERE poll_id = %s AND user_id = %s
    """, (poll_id, user_id))

    if existing:
        raise HTTPException(status_code=409, detail="User already voted on this poll")

    # 3. Validate vote payload matches poll type
    if poll['poll_type'] in ('binary', 'single'):
        if vote.option_id is None:
            raise HTTPException(status_code=400, detail="option_id required for this poll type")
        # Verify option belongs to this poll
        option_check = execute_query("""
            SELECT id FROM polls.poll_options
            WHERE id = %s AND poll_id = %s
        """, (vote.option_id, poll_id))
        if not option_check:
            raise HTTPException(status_code=400, detail="option_id does not belong to this poll")

    elif poll['poll_type'] == 'rating':
        if vote.rating_value is None:
            raise HTTPException(status_code=400, detail="rating_value required for rating polls")

    # 4. Insert vote
    execute_query("""
        INSERT INTO polls.poll_votes (poll_id, option_id, user_id, rating_value)
        VALUES (%s, %s, %s, %s)
    """, (poll_id, vote.option_id, user_id, vote.rating_value))

    # 5. Return updated poll state
    return await get_poll(poll_id, user_id)

@router.post("/", response_model=PollCreated)
async def create_poll(
        request: PollCreate,
        user_id: int = Depends(get_current_user_id)
    ):
    conn = get_db_connection()
    slug = request.slug if request.slug else generate_unique_slug(request.title)
    poll_status = POLL_STATUS_MAP.get(request.status, 'draft')

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # 1. Insert content_block
            cur.execute("""
                INSERT INTO company.content_blocks 
                    (title, slug, deck, category_id, body, metadata, app_id, widget_size, author_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.title,
                slug,
                request.deck,
                request.category_id,
                request.body or '',
                json.dumps({"content_type": "app", "status": request.status}),
                request.app_id,
                request.widget_size or 'medium',
                user_id
            ))
            content_id = cur.fetchone()['id']

            # 2. Insert poll
            cur.execute("""
                INSERT INTO polls.polls (content_id, question, poll_type, closes_at, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, content_id, question, poll_type, status, closes_at, created_at, status
            """, (
                content_id,
                request.question,
                request.poll_type,
                request.closes_at,
                poll_status,
                user_id
            ))
            poll = dict(cur.fetchone())
            poll_id = poll['id']

            # 3. Insert options
            if request.poll_type == 'binary':
                options_to_insert = [(text, i) for i, text in enumerate(BINARY_OPTIONS)]
            elif request.poll_type == 'single':
                options_to_insert = [(opt.text, opt.sequence_order) for opt in request.options]
            else:  # rating
                options_to_insert = []

            options = []
            for text, seq in options_to_insert:
                cur.execute("""
                    INSERT INTO polls.poll_options (poll_id, text, sequence_order)
                    VALUES (%s, %s, %s)
                    RETURNING id, text, sequence_order
                """, (poll_id, text, seq))
                row = dict(cur.fetchone())
                options.append(PollOptionResult(
                    id=row['id'],
                    text=row['text'],
                    sequence_order=row['sequence_order'],
                    vote_count=0
                ))

        conn.commit()

        return PollCreated(success=True, poll_id=poll_id, slug=slug)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

