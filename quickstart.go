// quickstart.go
// Small CLI to test RTUtils audit endpoints (asset lookup & prefetch)
// Usage examples:
//  go run quickstart.go lookup --asset W12-1234 --base http://localhost:8000 --token "Bearer ey..."
//  go run quickstart.go prefetch --session 42 --base http://localhost:8000 --token "Bearer ey..."
// Flags:
//  --base    Base URL of the running RTUtils server (default http://localhost:8000)
//  --token   Authorization header value (e.g. "Token abc..." or "Bearer ...")
//  --cookie  Raw Cookie header to send (e.g. "sessionid=...; csrftoken=...")
//  --insecure  Skip TLS verification (useful for self-signed certs)

package main

import (
	"bytes"
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "expected 'lookup' or 'prefetch' subcommands")
		os.Exit(2)
	}

	// Default from environment when available
	defaultBase := os.Getenv("RTUTILS_BASE")
	if defaultBase == "" {
		defaultBase = "http://localhost:8000"
	}
	defaultToken := os.Getenv("RTUTILS_TOKEN")

	base := flag.String("base", defaultBase, "Base URL of RTUtils server")
	token := flag.String("token", defaultToken, "Authorization header value (e.g. 'Token ...' or 'Bearer ...')")
	cookie := flag.String("cookie", "", "Raw Cookie header to send")
	insecure := flag.Bool("insecure", false, "Skip TLS certificate verification")
	// Parse common flags only for now; subcommands will use flag package again
	flag.CommandLine.Parse([]string{})

	sub := os.Args[1]

	switch sub {
	case "lookup":
		lookupCmd := flag.NewFlagSet("lookup", flag.ExitOnError)
		asset := lookupCmd.String("asset", "", "Asset ID to lookup (required)")
		lookupCmd.StringVar(base, "base", *base, "Base URL of RTUtils server")
		lookupCmd.StringVar(token, "token", *token, "Authorization header value")
		lookupCmd.StringVar(cookie, "cookie", *cookie, "Raw Cookie header to send")
		lookupCmd.BoolVar(insecure, "insecure", *insecure, "Skip TLS verification")
		lookupCmd.Parse(os.Args[2:])

		if *asset == "" {
			fmt.Fprintln(os.Stderr, "--asset is required")
			lookupCmd.Usage()
			os.Exit(2)
		}

		client := makeClient(*insecure)
		url := strings.TrimRight(*base, "/") + "/devices/audit/api/lookup-device/" + *asset + "/"
		req, _ := http.NewRequest("GET", url, nil)
		setAuth(req, *token, *cookie)
		fmt.Println("GET", url)
		resp, err := client.Do(req)
		if err != nil {
			fmt.Fprintln(os.Stderr, "request error:", err)
			os.Exit(1)
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		printResponse(resp.StatusCode, body)

	case "prefetch":
		pfCmd := flag.NewFlagSet("prefetch", flag.ExitOnError)
		session := pfCmd.String("session", "", "Session ID to prefetch (required)")
		poll := pfCmd.Bool("poll", true, "Poll status until completion")
		pfCmd.StringVar(base, "base", *base, "Base URL of RTUtils server")
		pfCmd.StringVar(token, "token", *token, "Authorization header value")
		pfCmd.StringVar(cookie, "cookie", *cookie, "Raw Cookie header to send")
		pfCmd.BoolVar(insecure, "insecure", *insecure, "Skip TLS verification")
		pfCmd.Parse(os.Args[2:])

		if *session == "" {
			fmt.Fprintln(os.Stderr, "--session is required")
			pfCmd.Usage()
			os.Exit(2)
		}

		client := makeClient(*insecure)
		url := strings.TrimRight(*base, "/") + "/devices/audit/api/prefetch-devices-async/" + *session + "/"
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer([]byte("{}")))
		setAuth(req, *token, *cookie)
		req.Header.Set("Content-Type", "application/json")
		fmt.Println("POST", url)
		resp, err := client.Do(req)
		if err != nil {
			fmt.Fprintln(os.Stderr, "request error:", err)
			os.Exit(1)
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		printResponse(resp.StatusCode, body)

		if resp.StatusCode >= 200 && resp.StatusCode < 300 && *poll {
			// try to parse job_id or status_url
			var m map[string]interface{}
			if err := json.Unmarshal(body, &m); err == nil {
				statusURL := ""
				if s, ok := m["status_url"].(string); ok && s != "" {
					statusURL = s
				} else if job, ok := m["job_id"].(string); ok && job != "" {
					statusURL = strings.TrimRight(*base, "/") + "/devices/audit/api/prefetch-status/" + job + "/"
				}
				if statusURL != "" {
					pollStatus(client, statusURL, *token, *cookie)
				} else {
					fmt.Fprintln(os.Stderr, "no status_url or job_id returned; cannot poll")
				}
			}
		}

	default:
		fmt.Fprintln(os.Stderr, "unknown subcommand:", sub)
		os.Exit(2)
	}
}

func setAuth(req *http.Request, token, cookie string) {
	if token != "" {
		// If token already contains a scheme (contains space like "Token abc"), use as-is.
		if strings.Contains(token, " ") {
			req.Header.Set("Authorization", token)
		} else {
			// Allow overriding default scheme via RTUTILS_AUTH_SCHEME env var; default to "Token".
			scheme := os.Getenv("RTUTILS_AUTH_SCHEME")
			if scheme == "" {
				scheme = "Token"
			}
			req.Header.Set("Authorization", scheme+" "+token)
		}
	}
	if cookie != "" {
		req.Header.Set("Cookie", cookie)
	}
}

func makeClient(insecure bool) *http.Client {
	tr := &http.Transport{}
	if insecure {
		tr.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	}
	return &http.Client{Timeout: 30 * time.Second, Transport: tr}
}

func printResponse(status int, body []byte) {
	fmt.Println("HTTP status:", status)
	var out bytes.Buffer
	if len(body) == 0 {
		fmt.Println("(empty body)")
		return
	}
	// Try to pretty print JSON
	if json.Valid(body) {
		if err := json.Indent(&out, body, "", "  "); err == nil {
			fmt.Println(out.String())
			return
		}
	}
	// fallback raw
	fmt.Println(string(body))
}

func pollStatus(client *http.Client, statusURL, token, cookie string) {
	fmt.Println("Polling status at:", statusURL)
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	timeout := time.After(5 * time.Minute)

	for {
		select {
		case <-ticker.C:
			req, _ := http.NewRequest("GET", statusURL, nil)
			setAuth(req, token, cookie)
			resp, err := client.Do(req)
			if err != nil {
				fmt.Fprintln(os.Stderr, "status request error:", err)
				return
			}
			b, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			printResponse(resp.StatusCode, b)
			// try to stop if status is completed/failed
			var m map[string]interface{}
			if err := json.Unmarshal(b, &m); err == nil {
				if s, ok := m["status"].(string); ok {
					if s == "completed" || s == "failed" {
						fmt.Println("Job finished with status:", s)
						return
					}
				}
			}
		case <-timeout:
			fmt.Fprintln(os.Stderr, "poll timeout reached")
			return
		}
	}
}
