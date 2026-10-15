use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;
use axum::{
    routing::{get, post},
    Router, Json, extract::{Path, State},
};
use tokio::time::timeout;
use tower::limit::RateLimit;
use tracing::info;

mod config;
mod db;
mod cache;
mod worker;

use config::Config;
use db::Database;
use cache::CacheService;

#[derive(Clone)]
pub struct AppState {
    pub db: Arc<Database>,
    pub cache: Arc<CacheService>,
    pub config: Arc<Config>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    info!("Initializing application...");

    let cfg = Arc::new(Config::from_env()?);
    let database = Arc::new(Database::new(&cfg).await?);
    let cache_service = Arc::new(CacheService::new(&cfg.redis_url).await?);

    let state = AppState {
        db: database,
        cache: cache_service,
        config: cfg.clone(),
    };

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/healthz", get(health_check))
        .route("/api/v1/items/:id", get(get_item))
        .route("/api/v1/items", post(create_item))
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.port));
    info!("Server listening on {}", addr);
    axum::serve(tokio::net::TcpListener::bind(&addr).await?, app).await?;

    Ok(())
}

async fn health_check() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

async fn get_item(
    Path(id): Path<String>,
    State(state): State<AppState>,
) -> Json<serde_json::Value> {
    if let Ok(Some(cached)) = state.cache.get(&id).await {
        return Json(serde_json::json!({ "item": cached, "source": "cache" }));
    }
    Json(serde_json::json!({ "item": id, "source": "db" }))
}

async fn create_item(
    State(_state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "created", "data": payload }))
}
