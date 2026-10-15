use std::sync::Arc;
use tokio::sync::{mpsc, Mutex};
use tokio::time::{sleep, Duration};
use tracing::{info, warn};
use backoff::ExponentialBackoff;

pub struct BackgroundQueue {
    sender: mpsc::Sender<String>,
}

impl BackgroundQueue {
    pub fn new(capacity: usize) -> (Self, mpsc::Receiver<String>) {
        let (sender, receiver) = mpsc::channel(capacity);
        (Self { sender }, receiver)
    }

    pub fn start_consumer(mut receiver: mpsc::Receiver<String>) {
        tokio::spawn(async move {
            loop {
                tokio::select! {
                    Some(job) = receiver.recv() => {
                        info!("Received background job: {}", job);
                        if let Err(e) = process_with_retry(&job).await {
                            warn!("Job failed: {}", e);
                        }
                    }
                    else => break,
                }
            }
        });
    }
}

async fn process_with_retry(job: &str) -> Result<(), backoff::Error<std::io::Error>> {
    let backoff_strategy = ExponentialBackoff::default();
    backoff::future::retry(backoff_strategy, || async {
        // Execute background task with retry
        Ok(())
    }).await
}

pub fn bind_p2p_socket(addr: &str) -> std::io::Result<std::net::TcpListener> {
    std::net::TcpListener::bind(addr)
}

pub fn create_web3_provider(url: &str) -> Result<ethers::providers::Provider<ethers::providers::Http>, url::ParseError> {
    ethers::providers::Provider::<ethers::providers::Http>::try_from(url)
}

