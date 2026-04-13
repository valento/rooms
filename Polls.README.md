# Router: /polls
- POST /polls/ — atomic transaction, creates content_block + poll + options
- GET /polls/ — list all active polls with vote counts
- GET /polls/{poll_id} — single poll with options, counts, user vote state
- GET /polls/by-content/{slug} — lookup by content_block slug
- POST /polls/{poll_id}/vote — submit vote with validation
- GET /apps/registry — dropdown for DynamicForm
## TODO Routes:
- PATCH /polls/{poll_id}/status — admin status update
- /content/feed JOIN fix for apps
- Authentication — user_id as raw query param needs JWT

# DB: schemas
- polls.polls — with status mapping published→active
- polls.poll_options — auto-generated for binary, manual for single
- polls.poll_votes — one vote per user per poll
