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
&nbsp;&nbsp;
#
# LLM → MCP → DB Architecture
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
# <span style='color:red'>**!**</span> ---

&nbsp;&nbsp;&nbsp;&nbsp;

### Check for docker mapped port
```sh
docker port company_db 
# 5432/tcp -> 0.0.0.0:5432
# 5432/tcp -> [::]:5432

curl -v telnet://localhost:5432
# *   Trying 127.0.0.1:5432...
# * Connected to localhost (127.0.0.1) port 5432 (#0)


```