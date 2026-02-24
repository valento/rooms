# Full Text Search
## <span style='color:red'>**!**</span> Add tsvector data for FTS
```sh
 id            | integer                  |
 block_type    | character varying(50)    |
 title         | character varying(255)   |
 body          | text                     |
 metadata      | jsonb                    |
 search_vector | tsvector 

SELECT block_type, search_vector FROM company.block_content
#  ABOUT | '2015':7B 'busi':17B 'compani':2A 'develop':14B 'mission':10B 'simplifi':12B 'small':16B 'softwar':13B 'start':5B 'stori':3A

 ```

## <span style='color:red'>**!**</span> Create a function to populate *tsvector*
```sh
CREATE OR REPLACE FUNCTION company.update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'B');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

```

## <span style='color:red'>**!**</span> Create a trigger to run function before table-update
```sh
CREATE TRIGGER content_blocks_search_update
BEFORE INSERT OR UPDATE ON company.content_blocks
FOR EACH ROW
EXECUTE FUNCTION company.update_search_vector();

```
## <span style='color:red'>**!**</span> Index table by *tsvector* type (*search_vector* column)
```sh
# Indexes speed up seraches
CREATE INDEX idx_content_blocks_search 
ON company.content_blocks 
USING GIN (search_vector);
```
Example Ranking:
```sh
SELECT * from company.content_blocks;
SELECT block_type, ts_rank(search_vector, q) AS rank
FROM company.content_blocks, to_tsquery('english','business&software') AS q
WHERE search_vector @@ q
ORDER BY rank DESC;

#  block_type |    rank    
# ------------+------------
#  BLOG       | 0.98724616
#  ABOUT      | 0.38097197
# (2 rows)
```
# Add Semantics to Search
Semantics are Vectors, 436 to 1500, that generate spaces for each text chunk  
✅ Generating embeddings thorugh embedding model - all-MiniLM-L6-v2  
✅ Storing generated vectors in PostgreSQL - '*embedding*'  
✅ Cosine similarity search to compair semantic vectors  
✅ Building [Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrievals) API  

&nbsp;&nbsp;
#

# LLM → MCP → DB Architecture - local only, not for deployment
=======
### <span style='color: orange'> *(turns out this is not ncesary: I won't even use Claude and therefore - no MCP either ClaudeDesktop only works locally)*
# LLM → MCP → DB Architecture
(anyways this was done in company-mcp directory, check it out)

```sh
User → Website → Claude API
                   ↓
               MCP Protocol
                   ↓
             MCP Server (Python)
             ├── search_content()
             ├── get_block()
             ├── list_by_type()
             └── get_related()
                   ↓
               PostgreSQL
             (web_api role)
```
# <span style='color:red'>**! Steps to create semantic searches**</span>
## Table
```sql

CREATE TABLE company.content_blocks (
    id SERIAL PRIMARY KEY,
    -- block_type VARCHAR(50) NOT NULL CHECK (block_type IN ('ABOUT', 'SERVICES', 'CASE_STUDIES', 'BLOG')),
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    search_vector TSVECTOR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

```
## <span style='color:orange'>Function to update tsvector</span>
```sql

CREATE OR REPLACE FUNCTION company.update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'B');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

```
## <span style='color:orange'>Trigger update function before every insert</span>
```sql

CREATE TRIGGER content_blocks_search_update
BEFORE INSERT OR UPDATE ON company.content_blocks
FOR EACH ROW
EXECUTE FUNCTION company.update_search_vector();
CREATE TRIGGER

```
### <span style='color:orange'>Test it without indexation
```sql

INSERT INTO company.content_blocks (block_type, title, body, metadata)
VALUES (
    'ABOUT',
    'Our Company Story',
    'We started in 2015 with a mission to simplify software development for small businesses.',
    '{"section": "history"}'
);
-- INSERT 0 1
-- Test full text search
SELECT block_type, title FROM company.content_blocks WHERE search_vector @@ to_tsquery('english','business');
--  block_type |                   title                   
-- ------------+-------------------------------------------
--  ABOUT      | Our Company Story
--  SERVICES   | Mobile Apps
--  BLOG       | Why Small Businesses Need Custom Software
-- (3 rows)

-- or

-- @@ to_tsquery('english','business | success') or @@ to_tsquery('english','business & success')
```

### <span style='color:orange'>Index search_vector (tsvector) with GIN</span>
```sql
CREATE INDEX idx_content_blocks_search 
ON company.content_blocks 
USING GIN (search_vector);
-- CREATE INDEX

```

### <span style='color:orange'>Test again: GIN-indexed tsvector</span>
```sql
SELECT 
    block_type, 
    title, 
    ts_rank(search_vector, to_tsquery('english', 'software')) AS rank
FROM company.content_blocks 
WHERE search_vector @@ to_tsquery('english', 'software')
ORDER BY rank DESC;

--  block_type |                   title                   |    rank    
-- ------------+-------------------------------------------+------------
--  BLOG       | Why Small Businesses Need Custom Software | 0.66871977
--  ABOUT      | Our Company Story                         | 0.24317084
-- (2 rows)

```
&nbsp;&nbsp;&nbsp;&nbsp;
#  


### Check for docker mapped port
```sh
docker port company_db 
# 5432/tcp -> 0.0.0.0:5432
# 5432/tcp -> [::]:5432

curl -v telnet://localhost:5432
# *   Trying 127.0.0.1:5432...
# * Connected to localhost (127.0.0.1) port 5432 (#0)


```
