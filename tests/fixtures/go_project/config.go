package main

import (
	"os"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Port            string
	DatabaseURL     string
	RedisAddr       string
	MaxOpenConns    int
	MaxIdleConns    int
	RequestTimeout  time.Duration
}

func LoadConfig() (*Config, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")

	viper.SetDefault("PORT", "8080")
	viper.SetDefault("MAX_OPEN_CONNS", 25)
	viper.SetDefault("MAX_IDLE_CONNS", 10)

	port := os.Getenv("PORT")
	if port == "" {
		port = viper.GetString("PORT")
	}

	dbURL := os.Getenv("DATABASE_URL")
	redisAddr := os.Getenv("REDIS_ADDR")

	return &Config{
		Port:           port,
		DatabaseURL:    dbURL,
		RedisAddr:      redisAddr,
		MaxOpenConns:   viper.GetInt("MAX_OPEN_CONNS"),
		MaxIdleConns:   viper.GetInt("MAX_IDLE_CONNS"),
		RequestTimeout: 5 * time.Second,
	}, nil
}
