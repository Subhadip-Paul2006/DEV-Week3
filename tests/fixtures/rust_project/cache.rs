use redis::AsyncCommands;
use std::time::Duration;

pub struct CacheService {
    client: redis::Client,
}

impl CacheService {
    pub async fn new(redis_url: &str) -> Result<Self, redis::RedisError> {
        let client = redis::Client::open(redis_url)?;
        Ok(Self { client })
    }

    pub async fn get(&self, key: &str) -> Result<Option<String>, redis::RedisError> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let res: Option<String> = conn.get(key).await?;
        Ok(res)
    }

    pub async fn set(&self, key: &str, val: &str, ttl_secs: u64) -> Result<(), redis::RedisError> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        conn.set_ex(key, val, ttl_secs).await?;
        Ok(())
    }
}
