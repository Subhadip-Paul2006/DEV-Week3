use sqlx::postgres::PgPoolOptions;
use sqlx::{PgPool, Pool, Postgres};
use std::time::Duration;
use crate::config::Config;

pub struct Database {
    pub pool: PgPool,
}

impl Database {
    pub async fn new(cfg: &Config) -> Result<Self, sqlx::Error> {
        // Configure connection pooling
        let pool = PgPoolOptions::new()
            .max_connections(cfg.max_connections)
            .min_connections(5)
            .acquire_timeout(Duration::from_secs(3))
            .idle_timeout(Duration::from_secs(600))
            .connect(&cfg.database_url)
            .await?;

        Ok(Self { pool })
    }

    pub async fn fetch_item(&self, id: &str) -> Result<Option<String>, sqlx::Error> {
        let rec: Option<(String,)> = sqlx::query_as!("SELECT name FROM items WHERE id = $1")
            .bind(id)
            .fetch_optional(&self.pool)
            .await?;

        Ok(rec.map(|(name,)| name))
    }
}
