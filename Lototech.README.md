# LototechApp
### An Bulgarian lotery TOTO2 6/49 statistics application
## Update TOTO2 new drawings
- Update: ./toto/\<year\>.json
- Call API route
```sh
curl -X POST http://localhost:8000/toto2/import -H "Content-Type: application/json" -d @./toto/toto2_2026.json

```
