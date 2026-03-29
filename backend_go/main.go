/*
TechBuzz AI Agent — Go Backend (Gin Framework)
===============================================
High-performance alternative backend for the TechBuzz AI agent.
Identical API contract to the Python backend — swap either one.

Run:
    go mod tidy
    go run main.go

Or build for production:
    go build -o techbuzz-server .
    ANTHROPIC_API_KEY=sk-ant-... ./techbuzz-server

Environment Variables:
    ANTHROPIC_API_KEY  — Required. Your Anthropic API key.
    ADMIN_EMAIL        — Admin login email (default: owner@local)
    ADMIN_PASS         — Admin login password (default: configure-locally)
    PORT               — Server port (default: 8000)
    ALLOWED_ORIGINS    — Comma-separated CORS origins
*/

package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

// ── Config ────────────────────────────────────────────────────

var (
	AnthropicKey   = getEnv("ANTHROPIC_API_KEY", "")
    AdminEmail     = getEnv("ADMIN_EMAIL", "owner@local")
    AdminPass      = getEnv("ADMIN_PASS", "configure-locally")
	Port           = getEnv("PORT", "8000")
	AllowedOrigins = strings.Split(getEnv("ALLOWED_ORIGINS", "*"), ",")
	ModelID        = "claude-sonnet-4-20250514"
	MaxTokens      = 2048
)

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// ── Admin Token ───────────────────────────────────────────────

var AdminToken = func() string {
	h := sha256.New()
	h.Write([]byte(AdminEmail + ":" + AdminPass + ":techbuzz2024"))
	return fmt.Sprintf("%x", h.Sum(nil))
}()

func isAdmin(token string) bool {
	return token == AdminToken
}

// ── Rate Limiter ──────────────────────────────────────────────

type RateLimiter struct {
	mu      sync.Mutex
	calls   map[string][]time.Time
	limit   int
	window  time.Duration
}

func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		calls:  make(map[string][]time.Time),
		limit:  limit,
		window: window,
	}
	// Cleanup goroutine
	go func() {
		for range time.Tick(5 * time.Minute) {
			rl.mu.Lock()
			cutoff := time.Now().Add(-window)
			for ip, times := range rl.calls {
				var fresh []time.Time
				for _, t := range times {
					if t.After(cutoff) {
						fresh = append(fresh, t)
					}
				}
				if len(fresh) == 0 {
					delete(rl.calls, ip)
				} else {
					rl.calls[ip] = fresh
				}
			}
			rl.mu.Unlock()
		}
	}()
	return rl
}

func (rl *RateLimiter) Allow(ip string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()
	now := time.Now()
	cutoff := now.Add(-rl.window)
	var fresh []time.Time
	for _, t := range rl.calls[ip] {
		if t.After(cutoff) {
			fresh = append(fresh, t)
		}
	}
	if len(fresh) >= rl.limit {
		return false
	}
	rl.calls[ip] = append(fresh, now)
	return true
}

var limiter = NewRateLimiter(30, time.Minute)

// ── Request / Response Models ──────────────────────────────────

type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Messages  []ChatMessage `json:"messages" binding:"required"`
	System    string        `json:"system"`
	AdminMode bool          `json:"admin_mode"`
	WebSearch bool          `json:"web_search"`
	MaxTokens int           `json:"max_tokens"`
}

type AdminLoginRequest struct {
	Email    string `json:"email" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type EditRequest struct {
	Instruction    string `json:"instruction" binding:"required"`
	CurrentHTML    string `json:"current_html"`
	TargetSelector string `json:"target_selector"`
	AdminToken     string `json:"admin_token" binding:"required"`
}

type WebSearchRequest struct {
	Query      string `json:"query" binding:"required"`
	AdminToken string `json:"admin_token"`
}

// Anthropic API types
type AnthropicTool struct {
	Type    string `json:"type"`
	Name    string `json:"name"`
	MaxUses int    `json:"max_uses,omitempty"`
}

type AnthropicRequest struct {
	Model     string          `json:"model"`
	MaxTokens int             `json:"max_tokens"`
	System    string          `json:"system"`
	Messages  []ChatMessage   `json:"messages"`
	Tools     []AnthropicTool `json:"tools,omitempty"`
}

type ContentBlock struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
	Name string `json:"name,omitempty"`
}

type AnthropicResponse struct {
	ID         string         `json:"id"`
	Model      string         `json:"model"`
	Content    []ContentBlock `json:"content"`
	StopReason string         `json:"stop_reason"`
	Usage      map[string]int `json:"usage"`
}

// ── System Prompts ─────────────────────────────────────────────

const PublicSystem = `You are TechBuzz AI — an intelligent assistant for TechBuzz Systems,
India's leading tech recruitment company. You have access to real-time web search.

ALWAYS use web search for:
- Current job market trends and salary data in India
- Latest news about tech companies
- Factual questions requiring up-to-date information
- Any question where accuracy is critical

TechBuzz Systems:
- Specializes in tech recruitment for India's startup ecosystem
- Services: Contingency Recruitment, Retained Search, Contract/Freelance Staffing, Team Build-outs
- Industries: SaaS, Fintech, Healthtech, E-commerce, EdTech, Deep Tech/AI, Cybersecurity
- Key stats: 200+ placements, 50+ companies, 12-day avg hire, 92% retention
- Contact: configure locally | techbuzzsystems.in

You are also a POWERFUL CREATION ASSISTANT — like Claude AI. You can:
- Write complete, production-ready code in any language
- Create documents, reports, templates, and business content
- Design data structures, architectures, and system designs
- Answer any technical, scientific, or general knowledge question
- Help with writing, analysis, math, research

RULES:
- Always be accurate — use web search for facts you're not 100% sure about
- Never fabricate statistics, company details, or salary figures — search first
- Format code in proper markdown code blocks with language tags
- Be helpful, warm, and professional
- For recruitment needs, offer to connect them with the TechBuzz team`

const AdminSystem = `You are TechBuzz AI in ADMIN MODE for Piyush Mani (owner of TechBuzz Systems).

You have FULL CAPABILITIES including real-time web search:
1. Web search for current, accurate information
2. Complete code generation in any language
3. Website content editing via structured JSON instructions
4. Data analysis, reports, and business insights
5. Create any document, template, or content on demand

When asked to CHANGE THE WEBSITE, always include edit instructions at the END:
<SITE_EDITS>
[
  {"selector": ".hero-title", "action": "setText", "value": "Your new headline"},
  {"selector": ".hero-sub", "action": "setText", "value": "New subtext"},
  {"selector": "#contact", "action": "setStyle", "value": "background:#ff6b2b"},
  {"selector": ".nav-brand", "action": "setHTML", "value": "TechBuzz <span>Pro</span>"}
]
</SITE_EDITS>

Supported actions: setText, setHTML, setStyle, addClass, removeClass, setAttribute

Be analytical, precise, and thorough. Confirm every action you take.`

// ── Anthropic API Call ─────────────────────────────────────────

func callAnthropic(messages []ChatMessage, system string, maxTok int, useSearch bool) (*AnthropicResponse, error) {
	if AnthropicKey == "" {
		return nil, fmt.Errorf("ANTHROPIC_API_KEY not configured")
	}

	payload := AnthropicRequest{
		Model:     ModelID,
		MaxTokens: maxTok,
		System:    system,
		Messages:  messages,
	}
	if useSearch {
		payload.Tools = []AnthropicTool{
			{Type: "web_search_20250305", Name: "web_search", MaxUses: 5},
		}
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("x-api-key", AnthropicKey)
	req.Header.Set("anthropic-version", "2023-06-01")
	req.Header.Set("anthropic-beta", "web-search-2025-03-05")
	req.Header.Set("content-type", "application/json")

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("Anthropic API error %d: %s", resp.StatusCode, string(data[:min(len(data), 300)]))
	}

	var result AnthropicResponse
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func extractText(resp *AnthropicResponse) string {
	var parts []string
	for _, block := range resp.Content {
		if block.Type == "text" && block.Text != "" {
			parts = append(parts, block.Text)
		}
	}
	return strings.Join(parts, "\n")
}

func usedWebSearch(resp *AnthropicResponse) bool {
	for _, block := range resp.Content {
		if block.Type == "tool_use" && block.Name == "web_search" {
			return true
		}
	}
	return false
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ── Middleware ─────────────────────────────────────────────────

func rateLimitMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		ip := c.ClientIP()
		if !limiter.Allow(ip) {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error": "Rate limit exceeded. Please wait a moment.",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

// ── Route Handlers ─────────────────────────────────────────────

func handleRoot(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"service":    "TechBuzz AI Agent API",
		"version":    "1.0.0",
		"language":   "Go",
		"status":     "online",
		"endpoints":  []string{"/api/chat", "/api/admin/login", "/api/admin/edit", "/api/health"},
		"model":      ModelID,
		"web_search": true,
	})
}

func handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":      "ok",
		"timestamp":   time.Now().UTC().Format(time.RFC3339),
		"api_key_set": AnthropicKey != "",
		"model":       ModelID,
	})
}

func handleAdminLogin(c *gin.Context) {
	var req AdminLoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if strings.TrimSpace(req.Email) == AdminEmail && req.Password == AdminPass {
		log.Printf("Admin login: %s", req.Email)
		c.JSON(http.StatusOK, gin.H{
			"success":    true,
			"token":      AdminToken,
			"email":      req.Email,
			"expires_in": "session",
		})
		return
	}
	log.Printf("Failed admin login: %s", req.Email)
	c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
}

func handleChat(c *gin.Context) {
	var req ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.MaxTokens == 0 {
		req.MaxTokens = MaxTokens
	}

	system := req.System
	if system == "" {
		if req.AdminMode {
			system = AdminSystem
		} else {
			system = PublicSystem
		}
	}

	log.Printf("Chat | IP=%s | admin=%v | msgs=%d | search=%v",
		c.ClientIP(), req.AdminMode, len(req.Messages), req.WebSearch)

	result, err := callAnthropic(req.Messages, system, req.MaxTokens, req.WebSearch)
	if err != nil {
		log.Printf("Chat error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"response":        extractText(result),
		"used_web_search": usedWebSearch(result),
		"usage":           result.Usage,
		"model":           result.Model,
		"stop_reason":     result.StopReason,
	})
}

func handleAdminEdit(c *gin.Context) {
	var req EditRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if !isAdmin(req.AdminToken) {
		c.JSON(http.StatusForbidden, gin.H{"error": "Invalid admin token"})
		return
	}

	htmlCtx := req.CurrentHTML
	if len(htmlCtx) > 2000 {
		htmlCtx = htmlCtx[:2000]
	}

	editSystem := AdminSystem + fmt.Sprintf(`

The admin wants to edit the TechBuzz website.
Target selector hint: %s
Current HTML context:
%s
Generate the edit instructions in <SITE_EDITS>[...]</SITE_EDITS> tags.
Be precise with CSS selectors. Explain what you changed.`,
		req.TargetSelector, htmlCtx)

	messages := []ChatMessage{{Role: "user", Content: req.Instruction}}

	result, err := callAnthropic(messages, editSystem, 1000, false)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	text := extractText(result)

	// Extract SITE_EDITS
	var edits []map[string]string
	re := regexp.MustCompile(`<SITE_EDITS>([\s\S]*?)</SITE_EDITS>`)
	match := re.FindStringSubmatch(text)
	if len(match) > 1 {
		json.Unmarshal([]byte(strings.TrimSpace(match[1])), &edits)
	}

	cleanText := re.ReplaceAllString(text, "")
	cleanText = strings.TrimSpace(cleanText)

	log.Printf("Admin edit | instruction='%s...' | edits=%d", req.Instruction[:min(len(req.Instruction), 60)], len(edits))

	c.JSON(http.StatusOK, gin.H{
		"explanation": cleanText,
		"edits":       edits,
		"edit_count":  len(edits),
	})
}

func handleWebSearch(c *gin.Context) {
	var req WebSearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	messages := []ChatMessage{{
		Role:    "user",
		Content: "Search the web for: " + req.Query + ". Provide accurate, sourced information.",
	}}

	result, err := callAnthropic(
		messages,
		"You are a web search assistant. Always search and provide accurate sourced information.",
		800,
		true,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"query":  req.Query,
		"result": extractText(result),
		"usage":  result.Usage,
	})
}

func handleStats(c *gin.Context) {
	token := c.GetHeader("X-Admin-Token")
	if !isAdmin(token) {
		c.JSON(http.StatusForbidden, gin.H{"error": "Admin access required"})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"model":              ModelID,
		"web_search_enabled": true,
		"timestamp":          time.Now().UTC().Format(time.RFC3339),
	})
}

// ── Main ──────────────────────────────────────────────────────

func main() {
	fmt.Println(`
╔══════════════════════════════════════════════╗
║      TechBuzz AI Agent — Go Backend          ║
║      Gin Framework + Anthropic + Search      ║
╚══════════════════════════════════════════════╝`)

	if AnthropicKey == "" {
		fmt.Println("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
		fmt.Println("   Set it as an environment variable\n")
	}

	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())

	// CORS
	r.Use(cors.New(cors.Config{
		AllowOrigins:     AllowedOrigins,
		AllowMethods:     []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:     []string{"Content-Type", "X-Admin-Token", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Rate limit on all API routes
	api := r.Group("/api")
	api.Use(rateLimitMiddleware())

	// Routes
	r.GET("/", handleRoot)
	api.GET("/health", handleHealth)
	api.POST("/admin/login", handleAdminLogin)
	api.POST("/chat", handleChat)
	api.POST("/admin/edit", handleAdminEdit)
	api.POST("/search", handleWebSearch)
	api.GET("/stats", handleStats)

	addr := "0.0.0.0:" + Port
	fmt.Printf("✅ Server running at http://%s\n\n", addr)
	fmt.Printf("   Endpoints:\n")
	fmt.Printf("   GET  /api/health\n")
	fmt.Printf("   POST /api/chat\n")
	fmt.Printf("   POST /api/admin/login\n")
	fmt.Printf("   POST /api/admin/edit\n")
	fmt.Printf("   POST /api/search\n\n")

	if err := r.Run(addr); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
