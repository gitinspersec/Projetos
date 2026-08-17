/*
©AngelaMos | 2026
reporter.go

Reporter interface and format-dispatching factory

Defines the Reporter interface used by all output formatters and provides
New() to select the correct implementation based on a format string
("terminal", "json", "sarif"). Defaults to Terminal when the format is empty
or unrecognized.

Key exports:
  Reporter - interface with Report(w io.Writer, result *ScanResult) error
  New - factory returning Terminal, JSON, or SARIF reporters

Connects to:
  reporter/terminal.go - returned by New("terminal") or New("")
  reporter/json.go - returned by New("json")
  reporter/sarif.go - returned by New("sarif")
  cli/scan.go - calls New(format) and Report() after each scan
*/

package reporter

import (
	"io"

	"github.com/CarterPerez-dev/portia/pkg/types"
)

type Reporter interface {
	Report(w io.Writer, result *types.ScanResult) error
}

func New(format string) Reporter {
	switch format {
	case "json":
		return &JSON{}
	case "sarif":
		return &SARIF{}
	default:
		return &Terminal{}
	}
}
