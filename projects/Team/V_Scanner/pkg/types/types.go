/*
©AngelaMos | 2026
types.go

Shared domain types used across all packages in angela

Defines the core data structures that flow through the scan pipeline,
from parsed dependency specs through update resolution and into final
scan results. All packages import from here; nothing in this package
imports from internal packages.

Key exports:
  Dependency    - a single parsed dependency with name, spec, extras, markers, and group
  UpdateResult  - outcome of checking one dependency for a newer version
  Vulnerability - a single security advisory with severity, fix version, and link
  ScanResult    - aggregated output of a full scan run
*/

package types

import "time"

// Dependency represents a single parsed dependency from a pyproject.toml file
type Dependency struct {
	Name    string
	Spec    string
	Extras  []string
	Markers string
	Group   string
}

// UpdateResult holds the outcome of checking one dependency for updates
type UpdateResult struct {
	Name    string
	OldSpec string
	NewSpec string
	OldVer  string
	NewVer  string
	Change  string
	Skipped bool
	Reason  string
}

// Vulnerability represents a single security advisory for a package
type Vulnerability struct {
	ID       string
	Aliases  []string
	Summary  string
	Severity string
	FixedIn  string
	Link     string
}

// ScanResult holds the aggregated output of a full dependency scan
type ScanResult struct {
	Updates         []UpdateResult
	Vulnerabilities map[string][]Vulnerability
	TotalPackages   int
	TotalUpdated    int
	TotalVulns      int
	VulnsScanned    bool
	Duration        time.Duration
}
