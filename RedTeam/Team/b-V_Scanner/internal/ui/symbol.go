/*
©AngelaMos | 2026
symbol.go

Named Unicode symbol constants and horizontal rule helper for terminal output

Centralizes every UI symbol used across the CLI so output.go stays
readable without hard-coded Unicode literals. HRule generates divider
lines of any width.

Connects to:
  output.go - uses all symbol constants for formatting scan results
  banner.go - uses HRule for the logo divider line
*/

package ui

import "strings"

const (
	Arrow       = "→"
	ArrowRight  = "▸"
	ArrowUp     = "↑"
	Diamond     = "◆"
	Gem         = "◈"
	Star        = "✦"
	TriangleUp  = "▲"
	Check       = "✓"
	Cross       = "✗"
	Timer       = "⏱"
	DividerChar = "━"
)

func HRule(width int) string {
	return strings.Repeat(DividerChar, width)
}
