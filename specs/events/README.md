# Event Contracts

This directory will hold the canonical cross-service event model.

Initial channels to formalize:

- `engine.orders.incoming` (Redis list queue)
- `engine.orders.accepted`
- `engine.orders.rejected`
- `engine.trades.executed`
- `engine.books.updated`
- `feed.prices.updated`
- `market.settlement.candidate`
- `ws.broadcast.market`
- `ws.broadcast.user`

Questions to settle:

- whether Redis Streams should replace the current Redis list queue for order intake
- event idempotency and replay strategy
- whether trade events are persisted before or after pub/sub fanout

Current implementation note:

- order intake uses a Redis list queue consumed by the Rust matching engine
- fanout events use Redis Pub/Sub
