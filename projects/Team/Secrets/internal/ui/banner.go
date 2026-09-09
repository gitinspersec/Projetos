/*
©AngelaMos | 2026
banner.go

ASCII art banner renderer with optional anime art decoration

Defines the "portia" ASCII wordmark and an optional decorative block-art panel.
PrintBanner renders just the wordmark with a subtitle rule; PrintBannerWithArt
adds the full art block beneath it. Banner and art lines cycle through color
arrays for alternating red/blue styling.

Key exports:
  PrintBanner - wordmark banner for subcommand help pages and scan start
  PrintBannerWithArt - full banner with decorative art for root help

Connects to:
  ui/color.go - uses Red, Blue, White, WhiteItalic, HiWhite for styling
  ui/symbol.go - uses HRule for the divider line
  cli/root.go - calls PrintBannerWithArt for root help, PrintBanner for subcommands
  cli/scan.go, cli/git.go - call PrintBanner at scan start
*/

package ui

import "fmt"

var portiaBanner = []string{
	"                                             ",
	"░░░░░░   ░░░░░░  ░░░░░░  ░░░░░░░░ ░░  ░░░░░  ",
	"▒▒   ▒▒ ▒▒    ▒▒ ▒▒   ▒▒    ▒▒    ▒▒ ▒▒   ▒▒ ",
	"▒▒▒▒▒▒  ▒▒    ▒▒ ▒▒▒▒▒▒     ▒▒    ▒▒ ▒▒▒▒▒▒▒ ",
	"▓▓      ▓▓    ▓▓ ▓▓   ▓▓    ▓▓    ▓▓ ▓▓   ▓▓ ",
	"██       ██████  ██   ██    ██    ██ ██   ██ ",
	"",
}

var bannerColors = []func(a ...any) string{
	Red,
	Blue,
	Red,
	Blue,
	Red,
}

var animeArt = []string{
	"⣿⣿⣿⣿⣿⣷⣿⣿⣿⡅⡹⢿⠆⠙⠋⠉⠻⠿⣿⣿⣿⣿⣿⣿⣮⠻⣦⡙⢷⡑⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣌⠡⠌⠂⣙⠻⣛⠻⠷⠐⠈⠛⢱⣮⣷⣽⣿",
	"⣿⣿⣿⣿⡇⢿⢹⣿⣶⠐⠁⠀⣀⣠⣤⠄⠀⠀⠈⠙⠻⣿⣿⣿⣦⣵⣌⠻⣷⢝⠦⠚⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢟⣻⣿⣊⡃⠀⣙⠿⣿⣿⣿⣎⢮⡀⢮⣽⣿⣿",
	"⢿⣿⣿⣿⣧⡸⡎⡛⡩⠖⠀⣴⣿⣿⣿⠀⠀⠀⠀⠸⠇⠀⠙⢿⣿⣿⣿⣷⣌⢷⣑⢷⣄⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣫⠶⠛⠉⠀⠁⠀⠈⠈⠀⠠⠜⠻⣿⣆⢿⣼⣿⣿⣿",
	"⢐⣿⣿⣿⣿⣧⢧⣧⢻⣦⢀⣹⣿⣿⣿⣇⠀⠄⠀⠀⠀⡀⠀⠈⢻⣿⣿⣿⣿⣷⣝⢦⡹⠷⡙⢿⣿⣿⣿⣿⣿⣿⣿⣿⠈⠁⠀⠀⠀⠁⠀⠀⠀⠱⣶⣄⡀⠀⠈⠛⠜⣿⣿⣿⣿",
	"⠀⠊⢫⣿⣏⣿⡌⣼⣄⢫⡌⣿⣿⣿⣿⣿⣦⡈⠲⣄⣤⣤⡡⢀⣠⣿⣿⣿⣿⣿⣿⣷⣼⣍⢬⣦⡙⣿⣿⣿⣿⣿⣯⢁⡄⠀⡀⡀⠀⠄⢈⣠⢪⠀⣿⣿⣿⣦⠀⢉⢂⠹⡿⣿⣿",
	"⠀⠀⠄⢹⢃⢻⣟⠙⣿⣦⠱⢻⣿⣿⣿⣿⣿⣿⣷⣬⣍⣭⣥⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⡙⢿⣼⡿⣿⣿⣿⣿⣿⣷⣄⠘⣱⢦⣤⡴⡿⢈⣼⣿⣿⣿⣇⣴⣶⣮⣅⢻⣿⡏",
	"⠀⠀⠈⠹⣇⢡⢿⡆⠻⣿⣷⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣍⡻⣿⣟⣻⣿⣿⣿⣿⣷⣦⣥⣬⣤⣴⣾⣿⣿⣿⣿⣷⣿⣿⣿⣿⣷⡜⠃",
	"⠀⠀⠀⢀⣘⠈⢂⠃⣧⡹⣿⣷⡄⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣮⣅⡙⢿⣟⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠋⡕⠂",
	"⠀⠀⠀⠀⠀⠀⠛⢷⣜⢷⡌⠻⣿⣿⣦⣝⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣹⣷⣦⣹⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠉⠃⠀",
}

var artColors = []func(a ...any) string{
	Blue,
	Blue,
	Blue,
	Red,
	Red,
	Red,
	Blue,
	Blue,
	Blue,
}

func PrintBanner() {
	fmt.Println()
	fmt.Println()
	for i, line := range portiaBanner {
		c := bannerColors[i%len(bannerColors)]
		fmt.Printf("  %s\n", c(line))
	}
	fmt.Printf("  %s\n", HiWhite(HRule(52)))
	fmt.Printf(
		"  %s\n\n",
		WhiteItalic(
			"Secrets scanner for git repos and config files",
		),
	)
}

func PrintBannerWithArt() {
	fmt.Println()
	for i, line := range portiaBanner {
		c := bannerColors[i%len(bannerColors)]
		fmt.Printf("  %s\n", c(line))
	}
	fmt.Printf("  %s\n", White(HRule(64)))
	fmt.Printf(
		"  %s\n",
		WhiteItalic(
			"Secrets scanner for git repos and config files",
		),
	)
	fmt.Println()
	for i, line := range animeArt {
		c := artColors[i%len(artColors)]
		fmt.Printf("  %s\n", c(line))
	}
	fmt.Println()
}
