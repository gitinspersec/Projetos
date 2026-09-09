/*
©AngelaMos | 2026
banner.go

ASCII art banner renderer for the angela CLI header

Renders the ANGELA logo in alternating red and blue before every command.
The help command gets an extended variant with an anime-art block printed
below the logo.

Key exports:
  PrintBanner        - compact banner printed before each command run
  PrintBannerWithArt - extended version with the full ASCII art block

Connects to:
  update.go - calls PrintBanner in PersistentPreRun and PrintBannerWithArt in the help override
  color.go  - uses Red, Blue, White, HiBlackItalic
  symbol.go - uses HRule for the divider line
*/

package ui

import "fmt"

var angelaBanner = []string{
	" ▄▀▄ █▄ █ ▄▀  ██▀ █   ▄▀▄ ",
	" █▀█ █ ▀█ ▀▄█ █▄▄ █▄▄ █▀█ ",
}

var bannerColors = []func(a ...any) string{
	Red,
	Blue,
}

var animeArt = []string{
	"⣿⣿⣿⡷⠊⡢⡹⣦⡑⢂⢕⢂⢕⢂⢕⢂⠕⠔⠌⠝⠛⠶⠶⢶⣦⣄⢂⢕⢂⢕",
	"⣿⣿⠏⣠⣾⣦⡐⢌⢿⣷⣦⣅⡑⠕⠡⠐⢿⠿⣛⠟⠛⠛⠛⠛⠡⢷⡈⢂⢕⢂",
	"⠟⣡⣾⣿⣿⣿⣿⣦⣑⠝⢿⣿⣿⣿⣿⣿⡵⢁⣤⣶⣶⣿⢿⢿⢿⡟⢻⣤⢑⢂",
	"⣾⣿⣿⡿⢟⣛⣻⣿⣿⣿⣦⣬⣙⣻⣿⣿⣷⣿⣿⢟⢝⢕⢕⢕⢕⢽⣿⣿⣷⣔",
	"⣿⣿⠵⠚⠉⢀⣀⣀⣈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣗⢕⢕⢕⢕⢕⢕⣽⣿⣿⣿⣿",
	"⢷⣂⣠⣴⣾⡿⡿⡻⡻⣿⣿⣴⣿⣿⣿⣿⣿⣿⣷⣵⣵⣵⣷⣿⣿⣿⣿⣿⣿⡿",
	"⢌⠻⣿⡿⡫⡪⡪⡪⡪⣺⣿⣿⣿⣿⣿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃",
	"⠣⡁⠹⡪⡪⡪⡪⣪⣾⣿⣿⣿⣿⠋⠐⢉⢍⢄⢌⠻⣿⣿⣿⣿⣿⣿⣿⣿⠏⠈",
	"⡣⡘⢄⠙⣾⣾⣾⣿⣿⣿⣿⣿⣿⡀⢐⢕⢕⢕⢕⢕⡘⣿⣿⣿⣿⣿⣿⠏⠠⠈",
	"⠌⢊⢂⢣⠹⣿⣿⣿⣿⣿⣿⣿⣿⣧⢐⢕⢕⢕⢕⢕⢅⣿⣿⣿⣿⡿⢋⢜⠠⠈",
}

var artColors = []func(a ...any) string{
	Red,
	Red,
	Blue,
	Blue,
	Red,
	Red,
	Blue,
	Blue,
	Blue,
	Red,
}

func PrintBanner() {
	fmt.Println()
	fmt.Println()
	for i, line := range angelaBanner {
		c := bannerColors[i%len(bannerColors)]
		fmt.Printf("  %s\n", c(line))
	}
	fmt.Printf("  %s\n", White(HRule(52)))
	fmt.Printf(
		"  %s\n\n",
		HiBlackItalic(
			"Python dependency updater & vulnerability scanner",
		),
	)
}

func PrintBannerWithArt() {
	fmt.Println()
	for i, line := range angelaBanner {
		c := bannerColors[i%len(bannerColors)]
		fmt.Printf("  %s\n", c(line))
	}
	fmt.Printf("  %s\n", White(HRule(52)))
	fmt.Printf(
		"  %s\n",
		HiBlackItalic(
			"Python dependency updater & vulnerability scanner",
		),
	)
	fmt.Println()
	for i, line := range animeArt {
		c := artColors[i%len(artColors)]
		fmt.Printf("  %s\n", c(line))
	}
	fmt.Println()
}
