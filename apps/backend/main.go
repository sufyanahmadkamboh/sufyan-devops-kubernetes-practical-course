// The course's backend: a tiny API whose only job is to make Kubernetes concepts visible.
//
//	GET /             {"message", "version", "pod"}: which version and which Pod answered (rolling updates, Services)
//	GET /api/visits   a counter stored in PostgreSQL (storage, Secrets, DNS); 503 when no database is configured
//	GET /api/config   the configuration the Pod received, the password only as "set"/"not set" (ConfigMaps, Secrets)
//	GET /api/burn     uses CPU for ?ms= milliseconds (default 200), so the autoscaler has something to react to
//	GET /livez        200 while the process runs (liveness probe)
//	GET /readyz       200 when the API can serve: the database answers, or no database is configured (readiness)
//
// Configuration, all optional: PORT (8080), MESSAGE, APP_VERSION, LOG_LEVEL, STARTUP_DELAY (seconds before the
// server starts listening, for startup probes), DB_HOST, DB_PORT (5432), DB_USER, DB_NAME, and the password as
// DB_PASSWORD or, preferably, DB_PASSWORD_FILE (a mounted Secret).
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func password() (string, string) {
	if file := os.Getenv("DB_PASSWORD_FILE"); file != "" {
		b, err := os.ReadFile(file)
		if err != nil {
			return "", "file " + file + " not readable"
		}
		return strings.TrimSpace(string(b)), "set (from file)"
	}
	if v := os.Getenv("DB_PASSWORD"); v != "" {
		return v, "set (from environment)"
	}
	return "", "not set"
}

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	port := env("PORT", "8080")
	version := env("APP_VERSION", "dev")
	pod, _ := os.Hostname()

	if d, err := strconv.Atoi(os.Getenv("STARTUP_DELAY")); err == nil && d > 0 {
		log.Info("slow start", "seconds", d)
		time.Sleep(time.Duration(d) * time.Second)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	var pool *pgxpool.Pool
	pw, pwState := password()
	if host := os.Getenv("DB_HOST"); host != "" {
		u := url.URL{Scheme: "postgres", User: url.UserPassword(env("DB_USER", "app"), pw),
			Host: host + ":" + env("DB_PORT", "5432"), Path: env("DB_NAME", "app"), RawQuery: "sslmode=disable&connect_timeout=3"}
		var err error
		if pool, err = pgxpool.New(ctx, u.String()); err != nil {
			log.Error("database configuration", "error", err)
			os.Exit(1)
		}
		defer pool.Close()
	}
	schema := func(c context.Context) error {
		_, err := pool.Exec(c, "CREATE TABLE IF NOT EXISTS visits (id INT PRIMARY KEY, n BIGINT NOT NULL); "+
			"INSERT INTO visits VALUES (1, 0) ON CONFLICT DO NOTHING")
		return err
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"message": env("MESSAGE", "Hello from the backend"), "version": version, "pod": pod})
	})
	mux.HandleFunc("GET /livez", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "alive"})
	})
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		if pool != nil {
			c, cancel := context.WithTimeout(r.Context(), 2*time.Second)
			defer cancel()
			if err := pool.Ping(c); err != nil {
				writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "database unavailable"})
				return
			}
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ready"})
	})
	mux.HandleFunc("GET /api/config", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"message": env("MESSAGE", "Hello from the backend"),
			"log_level": env("LOG_LEVEL", "info"), "db_host": env("DB_HOST", "(none)"), "db_password": pwState})
	})
	mux.HandleFunc("GET /api/visits", func(w http.ResponseWriter, r *http.Request) {
		if pool == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "no database configured (DB_HOST)"})
			return
		}
		var n int64
		err := schema(r.Context())
		if err == nil {
			err = pool.QueryRow(r.Context(), "UPDATE visits SET n = n + 1 WHERE id = 1 RETURNING n").Scan(&n)
		}
		if err != nil {
			log.Error("visits", "error", err)
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "database error: " + err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"visits": n, "pod": pod})
	})
	mux.HandleFunc("GET /api/burn", func(w http.ResponseWriter, r *http.Request) {
		ms, err := strconv.Atoi(r.URL.Query().Get("ms"))
		if err != nil || ms <= 0 || ms > 5000 {
			ms = 200
		}
		end, x := time.Now().Add(time.Duration(ms)*time.Millisecond), 0
		for time.Now().Before(end) {
			x++
		}
		writeJSON(w, http.StatusOK, map[string]any{"burned_ms": ms, "pod": pod, "loops": x})
	})

	srv := &http.Server{Addr: ":" + port, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdown)
	}()
	log.Info("listening", "port", port, "version", version, "pod", pod)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	log.Info("stopped")
}
