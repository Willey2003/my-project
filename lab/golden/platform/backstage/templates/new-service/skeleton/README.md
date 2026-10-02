# ${{ values.name }}

${{ values.description }}

Created from the **new-service** golden path template. Owner: `${{ values.owner }}`, system: `${{ values.system }}`.

```bash
docker build -t ${{ values.name }}:dev .
docker run --rm -p 8080:8080 ${{ values.name }}:dev    # http://localhost:8080/healthz
```

Docs live in `docs/` (TechDocs); the catalog entry is `catalog-info.yaml`.
