# Table API Reference

Complete LOS API integration documentation.

## API Methods

### start_post()

Initiate new game round.

```python
from table_api import start_post

await start_post(round_id, config)
```

### deal_post()

Submit game results.

```python
from table_api import deal_post

await deal_post(round_id, result, config)
```

### finish_post()

Complete current round.

```python
from table_api import finish_post

await finish_post(round_id, config)
```

## Related Documentation

- [Table API Documentation](../../TABLEAPI_DOC/)

