/*
©AngelaMos | 2026
symbol.go

Unicode symbol constants and horizontal rule helper for terminal output

Defines Arrow, Diamond, Check, Warning, Shield, and other Unicode glyphs used
throughout the terminal reporter and CLI commands. HRule generates a repeated
divider character string of the given width.

Connects to:
  reporter/terminal.go - uses Arrow, Diamond, Warning, Check, Shield
  ui/banner.go - uses HRule and HiWhite for divider lines
  cli/root.go, cli/scan.go, cli/git.go - use symbols in status output
*/

package ui

import "strings"

const (
	Arrow       = "\u2192"
	ArrowRight  = "\u25b8"
	ArrowUp     = "\u2191"
	Diamond     = "\u25c6"
	Gem         = "\u25c8"
	Star        = "\u2726"
	TriangleUp  = "\u25b2"
	Check       = "\u2713"
	Cross       = "\u2717"
	Timer       = "\u23f1"
	Warning     = "\u26a0"
	Shield      = "\u25c9"
	DividerChar = "\u2501"
)

func HRule(width int) string {
	return strings.Repeat(DividerChar, width)
}
