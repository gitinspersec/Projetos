/*
©AngelaMos | 2026
config.go

Loads angela settings from .angela.toml or the [tool.angela] section in pyproject.toml

Implements a cascading resolution order: checks for a standalone
.angela.toml first, then falls back to [tool.angela] inside
pyproject.toml. Returns a zero-value Config if neither source is present.

Connects to:
  update.go - calls Load() before each scan or update run
*/

package config

import (
	"os"
	"strings"

	toml "github.com/pelletier/go-toml/v2"
)

// Config holds project-level angela settings loaded from .angela.toml
// or [tool.angela] in pyproject.toml
type Config struct {
	MinSeverity string   `toml:"min-severity"`
	Ignore      []string `toml:"ignore"`
	IgnoreVulns []string `toml:"ignore-vulns"`
}

type pyprojectWrapper struct {
	Tool struct {
		Angela Config `toml:"angela"`
	} `toml:"tool"`
}

// Load reads angela configuration using a cascading resolution order:
// .angela.toml in current directory, then [tool.angela] in pyproject.toml
func Load(pyprojectPath string) Config {
	if cfg, err := loadFile(".angela.toml"); err == nil {
		return cfg
	}

	if cfg, ok := loadFromPyproject(pyprojectPath); ok {
		return cfg
	}

	return Config{}
}

func loadFile(path string) (Config, error) {
	data, err := os.ReadFile(path) //nolint:gosec
	if err != nil {
		return Config{}, err
	}

	var cfg Config
	if err := toml.Unmarshal(data, &cfg); err != nil {
		return Config{}, err
	}

	cfg.MinSeverity = strings.ToLower(
		strings.TrimSpace(cfg.MinSeverity),
	)
	return cfg, nil
}

func loadFromPyproject(path string) (Config, bool) {
	data, err := os.ReadFile(path) //nolint:gosec
	if err != nil {
		return Config{}, false
	}

	var wrapper pyprojectWrapper
	if err := toml.Unmarshal(data, &wrapper); err != nil {
		return Config{}, false
	}

	cfg := wrapper.Tool.Angela
	if cfg.MinSeverity == "" &&
		len(cfg.Ignore) == 0 &&
		len(cfg.IgnoreVulns) == 0 {
		return Config{}, false
	}

	cfg.MinSeverity = strings.ToLower(
		strings.TrimSpace(cfg.MinSeverity),
	)
	return cfg, true
}
