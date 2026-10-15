package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type Server struct {
	router *gin.Engine
	logger *zap.Logger
	cfg    *Config
	cache  *CacheService
	db     *Database
}

func NewServer(cfg *Config, logger *zap.Logger, cache *CacheService, db *Database) *Server {
	router := gin.Default()
	s := &Server{
		router: router,
		logger: logger,
		cfg:    cfg,
		cache:  cache,
		db:     db,
	}
	s.setupRoutes()
	return s
}

func (s *Server) setupRoutes() {
	s.router.GET("/health", s.handleHealth)
	s.router.GET("/healthz", s.handleHealth)
	s.router.GET("/api/v1/items/:id", s.handleGetItem)
	s.router.POST("/api/v1/items", s.handleCreateItem)
}

func (s *Server) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (s *Server) handleGetItem(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
	defer cancel()

	val, err := s.cache.Get(ctx, id)
	if err == nil && val != "" {
		c.JSON(http.StatusOK, gin.H{"item": val, "source": "cache"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"item": id, "source": "db"})
}

func (s *Server) handleCreateItem(c *gin.Context) {
	idempotencyKey := c.GetHeader("X-Idempotency-Key")
	if idempotencyKey == "" {
		s.logger.Warn("Missing idempotency key on create item")
	}
	c.JSON(http.StatusCreated, gin.H{"id": "item-123", "status": "created"})
}

func (s *Server) Run(addr string) error {
	srv := &http.Server{
		Addr:         addr,
		Handler:      s.router,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	s.logger.Info("Starting server", zap.String("addr", addr))
	return srv.ListenAndServe()
}
