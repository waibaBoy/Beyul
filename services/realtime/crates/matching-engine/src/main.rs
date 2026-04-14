use std::{env, fs, path::PathBuf};

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use dotenvy::from_path_override;
use redis::AsyncCommands;
use rust_decimal::prelude::Signed;
use rust_decimal::Decimal;
use shared::{
    scaffold_banner, EngineBookUpdatedEvent, EngineCommandType, EngineOrderCommand, EngineOrderStatus,
    EngineOrderUpdatedEvent, EngineTradeExecutedEvent,
};
use sqlx::{postgres::PgPoolOptions, FromRow, PgPool, Postgres, Row, Transaction};
use tracing::{error, info, warn};
use uuid::Uuid;

#[derive(Debug, Clone)]
struct EngineConfig {
    redis_url: String,
    postgres_url: String,
    orders_queue: String,
    orders_events_channel: String,
    trades_channel: String,
    books_channel: String,
}

impl EngineConfig {
    fn from_env() -> Self {
        load_env_files();
        Self {
            redis_url: resolve_redis_url(),
            postgres_url: resolve_postgres_url(),
            orders_queue: env::var("MATCHING_ENGINE_ORDERS_QUEUE")
                .unwrap_or_else(|_| "engine.orders.incoming".to_string()),
            orders_events_channel: env::var("MATCHING_ENGINE_ORDERS_EVENTS_CHANNEL")
                .unwrap_or_else(|_| "engine.orders.accepted".to_string()),
            trades_channel: env::var("MATCHING_ENGINE_TRADES_CHANNEL")
                .unwrap_or_else(|_| "engine.trades.executed".to_string()),
            books_channel: env::var("MATCHING_ENGINE_BOOKS_CHANNEL")
                .unwrap_or_else(|_| "engine.books.updated".to_string()),
        }
    }
}

fn load_env_files() {
    for candidate in env_candidates() {
        if candidate.exists() {
            let _ = from_path_override(candidate);
            break;
        }
    }
}

fn resolve_postgres_url() -> String {
    if let Some(dsn) = env::var("POSTGRES_DSN").ok().or_else(|| read_env_value("POSTGRES_DSN")) {
        return dsn.replace("postgresql+asyncpg://", "postgresql://");
    }
    env::var("POSTGRES_URL")
        .ok()
        .or_else(|| read_env_value("POSTGRES_URL"))
        .unwrap_or_else(|| "postgres://beyul:change_me@localhost:5432/beyul".to_string())
}

fn resolve_redis_url() -> String {
    if let Ok(redis_url) = env::var("REDIS_URL") {
        return redis_url;
    }
    let host = env::var("REDIS_HOST").unwrap_or_else(|_| "localhost".to_string());
    let port = env::var("REDIS_PORT").unwrap_or_else(|_| "6379".to_string());
    let password = env::var("REDIS_PASSWORD").unwrap_or_default();
    if password.is_empty() {
        format!("redis://{host}:{port}/0")
    } else {
        format!("redis://:{password}@{host}:{port}/0")
    }
}

fn env_candidates() -> [PathBuf; 3] {
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    [
        cwd.join("..").join("..").join(".env"),
        cwd.join("..").join(".env"),
        cwd.join(".env"),
    ]
}

fn read_env_value(key: &str) -> Option<String> {
    for candidate in env_candidates() {
        if !candidate.exists() {
            continue;
        }
        let contents = fs::read_to_string(candidate).ok()?;
        for line in contents.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            let (name, value) = trimmed.split_once('=')?;
            if name.trim() == key {
                return Some(value.trim().trim_matches('"').to_string());
            }
        }
    }
    None
}

#[derive(Debug, Clone, FromRow)]
struct EngineOrderRow {
    id: Uuid,
    market_id: Uuid,
    outcome_id: Uuid,
    profile_id: Uuid,
    asset_id: Uuid,
    asset_code: String,
    rail_mode: String,
    side: String,
    order_type: String,
    status: String,
    price: Option<Decimal>,
    matched_quantity: Decimal,
    remaining_quantity: Decimal,
    accepted_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, FromRow)]
struct ExistingPositionRow {
    id: Uuid,
    quantity: Decimal,
    average_entry_price: Option<Decimal>,
    realized_pnl: Decimal,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            env::var("RUST_LOG").unwrap_or_else(|_| "matching_engine=info,sqlx=warn,redis=warn".to_string()),
        )
        .init();

    let config = EngineConfig::from_env();
    info!("{}", scaffold_banner("matching-engine"));

    let redis_client =
        redis::Client::open(config.redis_url.clone()).context("failed to create redis client")?;
    let mut queue_conn = redis_client
        .get_multiplexed_async_connection()
        .await
        .context("failed to connect to redis queue")?;
    let mut publish_conn = redis_client
        .get_multiplexed_async_connection()
        .await
        .context("failed to connect to redis publisher")?;

    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&config.postgres_url)
        .await
        .context("failed to connect to postgres")?;

    loop {
        let (_, payload): (String, String) = redis::cmd("BRPOP")
            .arg(&config.orders_queue)
            .arg(0)
            .query_async(&mut queue_conn)
            .await
            .context("failed to read matching-engine queue")?;

        let command: EngineOrderCommand =
            serde_json::from_str(&payload).context("failed to parse engine order command")?;
        if !matches!(command.event_type, EngineCommandType::MatchOrder) {
            warn!(?command.event_type, "ignoring unsupported engine command");
            continue;
        }

        match process_order_command(&pool, &config, &mut publish_conn, command).await {
            Ok(()) => {}
            Err(error) => {
                error!(?error, "matching engine failed to process order command");
            }
        }
    }
}

async fn process_order_command(
    pool: &PgPool,
    config: &EngineConfig,
    publish_conn: &mut redis::aio::MultiplexedConnection,
    command: EngineOrderCommand,
) -> Result<()> {
    let mut tx = pool.begin().await.context("failed to begin transaction")?;

    let Some(taker) = lock_order(&mut tx, command.order_id).await? else {
        warn!(order_id = %command.order_id, "order disappeared before engine could load it");
        tx.commit().await?;
        return Ok(());
    };

    if taker.status == "cancelled" || taker.status == "rejected" || taker.status == "filled" {
        tx.commit().await?;
        return Ok(());
    }

    if taker.order_type != "limit" {
        let order_event = reject_order(&mut tx, &taker, "only limit orders are supported right now").await?;
        tx.commit().await?;
        publish_order_event(publish_conn, config, &order_event).await?;
        return Ok(());
    }

    let taker_price = taker
        .price
        .context("limit order is missing price in matching engine")?;
    let opposite_side = if taker.side == "buy" { "sell" } else { "buy" };
    let mut maker_candidates =
        fetch_match_candidates(&mut tx, &taker, opposite_side, taker_price).await?;

    let mut remaining = taker.remaining_quantity;
    let mut matched = taker.matched_quantity;
    let mut trade_events = Vec::new();

    for maker in maker_candidates.iter_mut() {
        if remaining <= Decimal::ZERO {
            break;
        }
        if maker.profile_id == taker.profile_id {
            continue;
        }
        let maker_price = maker
            .price
            .context("maker order is missing price in matching engine")?;
        let executable = match taker.side.as_str() {
            "buy" => maker_price <= taker_price,
            "sell" => maker_price >= taker_price,
            _ => false,
        };
        if !executable {
            continue;
        }

        let fill_quantity = remaining.min(maker.remaining_quantity);
        if fill_quantity <= Decimal::ZERO {
            continue;
        }
        let execution_price = maker_price;
        let gross_notional = fill_quantity * execution_price;
        let complementary_notional = fill_quantity - gross_notional;

        // Compute fees from market config — makers pay 0, takers pay platform_fee_bps
        let fee_row = sqlx::query(
            r#"
            select coalesce(platform_fee_bps, 200) as platform_fee_bps,
                   coalesce(creator_fee_bps, 0) as creator_fee_bps
            from public.markets where id = $1
            "#,
        )
        .bind(taker.market_id)
        .fetch_one(&mut *tx)
        .await
        .context("failed to fetch market fee config")?;

        let platform_fee_bps: i32 = fee_row.get("platform_fee_bps");
        let creator_fee_bps: i32 = fee_row.get("creator_fee_bps");
        let bps_divisor = Decimal::from(10_000);
        let platform_fee = gross_notional * Decimal::from(platform_fee_bps) / bps_divisor;
        let creator_fee = gross_notional * Decimal::from(creator_fee_bps) / bps_divisor;

        let trade_row = sqlx::query(
            r#"
            insert into public.trades (
                market_id,
                outcome_id,
                asset_id,
                rail_mode,
                maker_order_id,
                taker_order_id,
                maker_profile_id,
                taker_profile_id,
                quantity,
                price,
                gross_notional,
                platform_fee_amount,
                creator_fee_amount
            )
            values ($1, $2, $3, $4::public.rail_type, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            returning id, executed_at
            "#,
        )
        .bind(taker.market_id)
        .bind(taker.outcome_id)
        .bind(taker.asset_id)
        .bind(taker.rail_mode.clone())
        .bind(maker.id)
        .bind(taker.id)
        .bind(maker.profile_id)
        .bind(taker.profile_id)
        .bind(fill_quantity)
        .bind(execution_price)
        .bind(gross_notional)
        .bind(platform_fee)
        .bind(creator_fee)
        .fetch_one(&mut *tx)
        .await
        .context("failed to insert trade")?;

        record_trade_cash_ledger(
            &mut tx,
            &taker,
            maker,
            trade_row.get("id"),
            fill_quantity,
            gross_notional,
            complementary_notional,
        )
        .await
        .context("failed to write trade ledger entries")?;

        let taker_position_outcome_id = position_outcome_id_for_fill(&mut tx, &taker, execution_price).await?;
        let maker_position_outcome_id = position_outcome_id_for_fill(&mut tx, maker, execution_price).await?;
        let taker_position_price = position_price_for_fill(&taker, execution_price);
        let maker_position_price = position_price_for_fill(maker, execution_price);

        upsert_position(
            &mut tx,
            taker.market_id,
            taker_position_outcome_id,
            taker.profile_id,
            taker.asset_id,
            &taker.rail_mode,
            fill_quantity,
            taker_position_price,
            trade_row.get("executed_at"),
        )
        .await
        .context("failed to update taker position")?;

        upsert_position(
            &mut tx,
            maker.market_id,
            maker_position_outcome_id,
            maker.profile_id,
            maker.asset_id,
            &maker.rail_mode,
            fill_quantity,
            maker_position_price,
            trade_row.get("executed_at"),
        )
        .await
        .context("failed to update maker position")?;

        increment_market_totals(&mut tx, taker.market_id, gross_notional)
            .await
            .context("failed to update market totals")?;

        let maker_new_remaining = maker.remaining_quantity - fill_quantity;
        let maker_new_matched = maker.matched_quantity + fill_quantity;
        let maker_new_status = if maker_new_remaining <= Decimal::ZERO {
            "filled"
        } else {
            "partially_filled"
        };

        sqlx::query(
            r#"
            update public.orders
            set
                status = $2::public.order_status,
                matched_quantity = $3,
                remaining_quantity = $4,
                accepted_at = coalesce(accepted_at, timezone('utc', now())),
                engine_order_id = coalesce(engine_order_id, $5),
                updated_at = timezone('utc', now())
            where id = $1
            "#,
        )
        .bind(maker.id)
        .bind(maker_new_status)
        .bind(maker_new_matched)
        .bind(maker_new_remaining.max(Decimal::ZERO))
        .bind(maker.id.to_string())
        .execute(&mut *tx)
        .await
        .context("failed to update maker order")?;

        maker.remaining_quantity = maker_new_remaining.max(Decimal::ZERO);
        maker.matched_quantity = maker_new_matched;
        maker.status = maker_new_status.to_string();
        maker.accepted_at = Some(Utc::now());

        remaining -= fill_quantity;
        matched += fill_quantity;

        trade_events.push(EngineTradeExecutedEvent {
            trade_id: trade_row.get("id"),
            market_id: taker.market_id,
            outcome_id: taker.outcome_id,
            maker_order_id: maker.id,
            taker_order_id: taker.id,
            quantity: fill_quantity,
            price: execution_price,
            gross_notional,
            executed_at: trade_row.get("executed_at"),
        });
    }

    let taker_status = if matched <= Decimal::ZERO {
        EngineOrderStatus::Open
    } else if remaining <= Decimal::ZERO {
        EngineOrderStatus::Filled
    } else {
        EngineOrderStatus::PartiallyFilled
    };

    let accepted_at = Utc::now();
    sqlx::query(
        r#"
        update public.orders
        set
            status = $2::public.order_status,
            matched_quantity = $3,
            remaining_quantity = $4,
            accepted_at = coalesce(accepted_at, $5),
            engine_order_id = coalesce(engine_order_id, $6),
            updated_at = timezone('utc', now())
        where id = $1
        "#,
    )
    .bind(taker.id)
    .bind(order_status_to_db(&taker_status))
    .bind(matched)
    .bind(remaining.max(Decimal::ZERO))
    .bind(accepted_at)
    .bind(taker.id.to_string())
    .execute(&mut *tx)
    .await
    .context("failed to update taker order")?;

    let order_event = EngineOrderUpdatedEvent {
        order_id: taker.id,
        market_id: taker.market_id,
        outcome_id: taker.outcome_id,
        status: taker_status,
        matched_quantity: matched,
        remaining_quantity: remaining.max(Decimal::ZERO),
        accepted_at: Some(accepted_at),
        rejection_reason: None,
    };

    let book_event = build_book_event(&mut tx, taker.market_id, taker.outcome_id).await?;

    tx.commit().await.context("failed to commit match transaction")?;

    publish_order_event(publish_conn, config, &order_event).await?;
    for trade_event in &trade_events {
        publish_trade_event(publish_conn, config, trade_event).await?;
    }
    publish_book_event(publish_conn, config, &book_event).await?;

    info!(
        order_id = %taker.id,
        matched_quantity = %matched,
        remaining_quantity = %remaining.max(Decimal::ZERO),
        "engine processed order"
    );
    Ok(())
}

async fn lock_order(tx: &mut Transaction<'_, Postgres>, order_id: Uuid) -> Result<Option<EngineOrderRow>> {
    let order = sqlx::query_as::<_, EngineOrderRow>(
        r#"
        select
            o.id,
            o.market_id,
            o.outcome_id,
            o.profile_id,
            o.asset_id,
            a.code as asset_code,
            o.rail_mode::text as rail_mode,
            o.side::text as side,
            o.order_type::text as order_type,
            o.status::text as status,
            o.price,
            o.matched_quantity,
            o.remaining_quantity,
            o.accepted_at
        from public.orders o
        join public.assets a on a.id = o.asset_id
        where o.id = $1
        for update
        "#,
    )
    .bind(order_id)
    .fetch_optional(&mut **tx)
    .await
    .context("failed to load taker order")?;
    Ok(order)
}

async fn fetch_match_candidates(
    tx: &mut Transaction<'_, Postgres>,
    taker: &EngineOrderRow,
    opposite_side: &str,
    taker_price: Decimal,
) -> Result<Vec<EngineOrderRow>> {
    let query = if taker.side == "buy" {
        r#"
        select
            o.id,
            o.market_id,
            o.outcome_id,
            o.profile_id,
            o.asset_id,
            a.code as asset_code,
            o.rail_mode::text as rail_mode,
            o.side::text as side,
            o.order_type::text as order_type,
            o.status::text as status,
            o.price,
            o.matched_quantity,
            o.remaining_quantity,
            o.accepted_at
        from public.orders o
        join public.assets a on a.id = o.asset_id
        where
            o.market_id = $1
            and o.outcome_id = $2
            and o.side = $3::public.order_side
            and o.status in ('open', 'partially_filled')
            and o.price <= $4
        order by o.price asc, o.created_at asc
        for update
        "#
    } else {
        r#"
        select
            o.id,
            o.market_id,
            o.outcome_id,
            o.profile_id,
            o.asset_id,
            a.code as asset_code,
            o.rail_mode::text as rail_mode,
            o.side::text as side,
            o.order_type::text as order_type,
            o.status::text as status,
            o.price,
            o.matched_quantity,
            o.remaining_quantity,
            o.accepted_at
        from public.orders o
        join public.assets a on a.id = o.asset_id
        where
            o.market_id = $1
            and o.outcome_id = $2
            and o.side = $3::public.order_side
            and o.status in ('open', 'partially_filled')
            and o.price >= $4
        order by o.price desc, o.created_at asc
        for update
        "#
    };

    let rows = sqlx::query_as::<_, EngineOrderRow>(query)
        .bind(taker.market_id)
        .bind(taker.outcome_id)
        .bind(opposite_side)
        .bind(taker_price)
        .fetch_all(&mut **tx)
        .await
    .context("failed to fetch match candidates")?;
    Ok(rows)
}

fn position_price_for_fill(order: &EngineOrderRow, execution_price: Decimal) -> Decimal {
    if order.side == "buy" {
        execution_price
    } else {
        Decimal::ONE - execution_price
    }
}

async fn position_outcome_id_for_fill(
    tx: &mut Transaction<'_, Postgres>,
    order: &EngineOrderRow,
    execution_price: Decimal,
) -> Result<Uuid> {
    let _ = execution_price;
    if order.side == "buy" {
        return Ok(order.outcome_id);
    }

    // NOTE: Complementary outcome resolution assumes binary (2-outcome) markets.
    // For multi-outcome markets (3+ outcomes), this logic needs to be extended
    // to handle portfolio-level position netting rather than per-outcome pairing.
    let complementary_outcome_id = sqlx::query_scalar::<_, Uuid>(
        r#"
        select id
        from public.market_outcomes
        where market_id = $1 and id <> $2
        order by outcome_index asc
        limit 1
        "#,
    )
    .bind(order.market_id)
    .bind(order.outcome_id)
    .fetch_optional(&mut **tx)
    .await
    .context("failed to resolve complementary outcome")?;

    complementary_outcome_id.context("binary market is missing a complementary outcome")
}

async fn record_trade_cash_ledger(
    tx: &mut Transaction<'_, Postgres>,
    taker: &EngineOrderRow,
    maker: &EngineOrderRow,
    trade_id: Uuid,
    fill_quantity: Decimal,
    gross_notional: Decimal,
    complementary_notional: Decimal,
) -> Result<()> {
    let (buyer, seller) = if taker.side == "buy" {
        (taker, maker)
    } else {
        (maker, taker)
    };

    let buyer_account_id = ensure_user_ledger_account(
        tx,
        buyer.profile_id,
        buyer.asset_id,
        &buyer.asset_code,
        &buyer.rail_mode,
    )
    .await?;
    let seller_account_id = ensure_user_ledger_account(
        tx,
        seller.profile_id,
        seller.asset_id,
        &seller.asset_code,
        &seller.rail_mode,
    )
    .await?;
    let market_account_id = ensure_market_ledger_account(
        tx,
        taker.market_id,
        taker.asset_id,
        &taker.asset_code,
        &taker.rail_mode,
    )
    .await?;

    let transaction_id: Uuid = sqlx::query_scalar(
        r#"
        insert into public.ledger_transactions (
            transaction_type,
            market_id,
            order_id,
            trade_id,
            initiated_by,
            description,
            metadata
        )
        values (
            'bet_lock'::public.ledger_transaction_type,
            $1,
            $2,
            $3,
            $4,
            $5,
            '{}'::jsonb
        )
        returning id
        "#,
    )
    .bind(taker.market_id)
    .bind(taker.id)
    .bind(trade_id)
    .bind(taker.profile_id)
    .bind(format!("Collateral lock for trade {} on market {}", trade_id, taker.market_id))
    .fetch_one(&mut **tx)
    .await
    .context("failed to create trade ledger transaction")?;

    sqlx::query(
        r#"
        insert into public.ledger_entries (
            transaction_id,
            ledger_account_id,
            direction,
            amount,
            metadata
        )
        values
            ($1, $2, 'credit'::public.ledger_entry_direction, $5, '{}'::jsonb),
            ($1, $3, 'credit'::public.ledger_entry_direction, $6, '{}'::jsonb),
            ($1, $4, 'debit'::public.ledger_entry_direction, $7, '{}'::jsonb)
        "#,
    )
    .bind(transaction_id)
    .bind(buyer_account_id)
    .bind(seller_account_id)
    .bind(market_account_id)
    .bind(gross_notional)
    .bind(complementary_notional)
    .bind(fill_quantity)
    .execute(&mut **tx)
    .await
    .context("failed to write trade ledger entries")?;

    Ok(())
}

async fn ensure_user_ledger_account(
    tx: &mut Transaction<'_, Postgres>,
    profile_id: Uuid,
    asset_id: Uuid,
    asset_code: &str,
    rail_mode: &str,
) -> Result<Uuid> {
    let account_code = format!("USER::{profile_id}::{asset_code}::{rail_mode}");
    if let Some(existing) = sqlx::query_scalar::<_, Uuid>(
        r#"
        select id
        from public.ledger_accounts
        where account_code = $1
        "#,
    )
    .bind(&account_code)
    .fetch_optional(&mut **tx)
    .await
    .context("failed to look up user ledger account")?
    {
        return Ok(existing);
    }

    let created = sqlx::query_scalar::<_, Uuid>(
        r#"
        insert into public.ledger_accounts (
            account_code,
            owner_type,
            owner_profile_id,
            asset_id,
            rail_mode,
            is_system,
            metadata
        )
        values (
            $1,
            'user'::public.ledger_owner_type,
            $2,
            $3,
            $4::public.rail_type,
            false,
            '{}'::jsonb
        )
        returning id
        "#,
    )
    .bind(&account_code)
    .bind(profile_id)
    .bind(asset_id)
    .bind(rail_mode)
    .fetch_one(&mut **tx)
    .await
    .context("failed to create user ledger account")?;

    Ok(created)
}

async fn ensure_market_ledger_account(
    tx: &mut Transaction<'_, Postgres>,
    market_id: Uuid,
    asset_id: Uuid,
    asset_code: &str,
    rail_mode: &str,
) -> Result<Uuid> {
    let account_code = format!("MARKET::{market_id}::{asset_code}::{rail_mode}");
    if let Some(existing) = sqlx::query_scalar::<_, Uuid>(
        r#"
        select id
        from public.ledger_accounts
        where account_code = $1
        "#,
    )
    .bind(&account_code)
    .fetch_optional(&mut **tx)
    .await
    .context("failed to look up market ledger account")?
    {
        return Ok(existing);
    }

    let created = sqlx::query_scalar::<_, Uuid>(
        r#"
        insert into public.ledger_accounts (
            account_code,
            owner_type,
            owner_market_id,
            asset_id,
            rail_mode,
            is_system,
            metadata
        )
        values (
            $1,
            'market'::public.ledger_owner_type,
            $2,
            $3,
            $4::public.rail_type,
            true,
            '{"purpose":"settlement"}'::jsonb
        )
        returning id
        "#,
    )
    .bind(&account_code)
    .bind(market_id)
    .bind(asset_id)
    .bind(rail_mode)
    .fetch_one(&mut **tx)
    .await
    .context("failed to create market ledger account")?;

    Ok(created)
}

async fn upsert_position(
    tx: &mut Transaction<'_, Postgres>,
    market_id: Uuid,
    outcome_id: Uuid,
    profile_id: Uuid,
    asset_id: Uuid,
    rail_mode: &str,
    delta_quantity: Decimal,
    trade_price: Decimal,
    trade_time: DateTime<Utc>,
) -> Result<()> {
    let existing = sqlx::query_as::<_, ExistingPositionRow>(
        r#"
        select
            id,
            quantity,
            average_entry_price,
            realized_pnl
        from public.positions
        where
            market_id = $1
            and outcome_id = $2
            and profile_id = $3
            and asset_id = $4
            and rail_mode = $5::public.rail_type
        for update
        "#,
    )
    .bind(market_id)
    .bind(outcome_id)
    .bind(profile_id)
    .bind(asset_id)
    .bind(rail_mode)
    .fetch_optional(&mut **tx)
    .await
    .context("failed to load existing position")?;

    let mut quantity = existing.as_ref().map(|row| row.quantity).unwrap_or(Decimal::ZERO);
    let mut average_entry_price = existing
        .as_ref()
        .and_then(|row| row.average_entry_price)
        .unwrap_or(Decimal::ZERO);
    let mut realized_pnl = existing.as_ref().map(|row| row.realized_pnl).unwrap_or(Decimal::ZERO);

    let old_quantity = quantity;
    let same_direction = old_quantity == Decimal::ZERO || old_quantity.signum() == delta_quantity.signum();

    if same_direction {
        let total_abs_quantity = old_quantity.abs() + delta_quantity.abs();
        let weighted_notional = (old_quantity.abs() * average_entry_price) + (delta_quantity.abs() * trade_price);
        quantity = old_quantity + delta_quantity;
        average_entry_price = if total_abs_quantity > Decimal::ZERO {
            weighted_notional / total_abs_quantity
        } else {
            Decimal::ZERO
        };
    } else {
        let closing_quantity = old_quantity.abs().min(delta_quantity.abs());
        realized_pnl += closing_quantity * (trade_price - average_entry_price) * old_quantity.signum();
        quantity = old_quantity + delta_quantity;
        if quantity == Decimal::ZERO {
            average_entry_price = Decimal::ZERO;
        } else if quantity.signum() != old_quantity.signum() {
            average_entry_price = trade_price;
        }
    }

    let net_cost = if quantity == Decimal::ZERO {
        Decimal::ZERO
    } else {
        quantity * average_entry_price
    };

    match existing {
        Some(row) => {
            sqlx::query(
                r#"
                update public.positions
                set
                    quantity = $2,
                    average_entry_price = $3,
                    net_cost = $4,
                    realized_pnl = $5,
                    unrealized_pnl = 0,
                    last_trade_at = $6,
                    updated_at = timezone('utc', now())
                where id = $1
                "#,
            )
            .bind(row.id)
            .bind(quantity)
            .bind(if quantity == Decimal::ZERO { None } else { Some(average_entry_price) })
            .bind(net_cost)
            .bind(realized_pnl)
            .bind(trade_time)
            .execute(&mut **tx)
            .await
            .context("failed to update position")?;
        }
        None => {
            sqlx::query(
                r#"
                insert into public.positions (
                    market_id,
                    outcome_id,
                    profile_id,
                    asset_id,
                    rail_mode,
                    quantity,
                    average_entry_price,
                    net_cost,
                    realized_pnl,
                    unrealized_pnl,
                    last_trade_at
                )
                values ($1, $2, $3, $4, $5::public.rail_type, $6, $7, $8, 0, 0, $9)
                "#,
            )
            .bind(market_id)
            .bind(outcome_id)
            .bind(profile_id)
            .bind(asset_id)
            .bind(rail_mode)
            .bind(quantity)
            .bind(Some(average_entry_price))
            .bind(net_cost)
            .bind(trade_time)
            .execute(&mut **tx)
            .await
            .context("failed to insert position")?;
        }
    }

    Ok(())
}

async fn increment_market_totals(
    tx: &mut Transaction<'_, Postgres>,
    market_id: Uuid,
    gross_notional: Decimal,
) -> Result<()> {
    sqlx::query(
        r#"
        update public.markets
        set
            total_volume = total_volume + $2,
            total_trades_count = total_trades_count + 1,
            updated_at = timezone('utc', now())
        where id = $1
        "#,
    )
    .bind(market_id)
    .bind(gross_notional)
    .execute(&mut **tx)
    .await
    .context("failed to increment market totals")?;
    Ok(())
}

async fn build_book_event(
    tx: &mut Transaction<'_, Postgres>,
    market_id: Uuid,
    outcome_id: Uuid,
) -> Result<EngineBookUpdatedEvent> {
    let best_bid: Option<Decimal> = sqlx::query_scalar(
        r#"
        select max(price)
        from public.orders
        where
            market_id = $1
            and outcome_id = $2
            and side = 'buy'
            and status in ('open', 'partially_filled')
        "#,
    )
    .bind(market_id)
    .bind(outcome_id)
    .fetch_one(&mut **tx)
    .await
    .context("failed to fetch best bid")?;

    let best_ask: Option<Decimal> = sqlx::query_scalar(
        r#"
        select min(price)
        from public.orders
        where
            market_id = $1
            and outcome_id = $2
            and side = 'sell'
            and status in ('open', 'partially_filled')
        "#,
    )
    .bind(market_id)
    .bind(outcome_id)
    .fetch_one(&mut **tx)
    .await
    .context("failed to fetch best ask")?;

    Ok(EngineBookUpdatedEvent {
        market_id,
        outcome_id,
        best_bid,
        best_ask,
        updated_at: Utc::now(),
    })
}

async fn reject_order(
    tx: &mut Transaction<'_, Postgres>,
    order: &EngineOrderRow,
    rejection_reason: &str,
) -> Result<EngineOrderUpdatedEvent> {
    sqlx::query(
        r#"
        update public.orders
        set
            status = 'rejected',
            rejection_reason = $2,
            updated_at = timezone('utc', now())
        where id = $1
        "#,
    )
    .bind(order.id)
    .bind(rejection_reason)
    .execute(&mut **tx)
    .await
    .context("failed to reject order")?;

    Ok(EngineOrderUpdatedEvent {
        order_id: order.id,
        market_id: order.market_id,
        outcome_id: order.outcome_id,
        status: EngineOrderStatus::Rejected,
        matched_quantity: order.matched_quantity,
        remaining_quantity: order.remaining_quantity,
        accepted_at: None,
        rejection_reason: Some(rejection_reason.to_string()),
    })
}

fn order_status_to_db(status: &EngineOrderStatus) -> &'static str {
    match status {
        EngineOrderStatus::PendingAcceptance => "pending_acceptance",
        EngineOrderStatus::Open => "open",
        EngineOrderStatus::PartiallyFilled => "partially_filled",
        EngineOrderStatus::Filled => "filled",
        EngineOrderStatus::Cancelled => "cancelled",
        EngineOrderStatus::Rejected => "rejected",
        EngineOrderStatus::Expired => "expired",
    }
}

async fn publish_order_event(
    publish_conn: &mut redis::aio::MultiplexedConnection,
    config: &EngineConfig,
    event: &EngineOrderUpdatedEvent,
) -> Result<()> {
    let payload = serde_json::to_string(event).context("failed to serialize order event")?;
    let _: usize = publish_conn
        .publish(&config.orders_events_channel, payload)
        .await
        .context("failed to publish order event")?;
    Ok(())
}

async fn publish_trade_event(
    publish_conn: &mut redis::aio::MultiplexedConnection,
    config: &EngineConfig,
    event: &EngineTradeExecutedEvent,
) -> Result<()> {
    let payload = serde_json::to_string(event).context("failed to serialize trade event")?;
    let _: usize = publish_conn
        .publish(&config.trades_channel, payload)
        .await
        .context("failed to publish trade event")?;
    Ok(())
}

async fn publish_book_event(
    publish_conn: &mut redis::aio::MultiplexedConnection,
    config: &EngineConfig,
    event: &EngineBookUpdatedEvent,
) -> Result<()> {
    let payload = serde_json::to_string(event).context("failed to serialize book event")?;
    let _: usize = publish_conn
        .publish(&config.books_channel, payload)
        .await
        .context("failed to publish book event")?;
    Ok(())
}
