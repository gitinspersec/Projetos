/*
©AngelaMos | 2026
git.go

"git" subcommand for scanning git repository history

Implements "portia git [repo-path]" which scans commit history (or only staged
changes with --staged) for leaked secrets. Accepts --branch, --since, --depth,
and --staged flags, merging them with values from the loaded config. Delegates
to executeScan in scan.go once the Git source is constructed.

Connects to:
  cli/root.go - registered as gitCmd via rootCmd.AddCommand
  cli/scan.go - calls executeScan() and applyRuleConfig()
  source/git.go - constructs NewGit() source
  rules/registry.go - calls NewRegistry() and RegisterBuiltins()
  ui/banner.go - calls PrintBanner() at scan start
*/

package cli

import (
	"github.com/spf13/cobra"

	"github.com/CarterPerez-dev/portia/internal/rules"
	"github.com/CarterPerez-dev/portia/internal/source"
	"github.com/CarterPerez-dev/portia/internal/ui"
)

var (
	gitBranch  string
	gitSince   string
	gitDepth   int
	stagedOnly bool
)

var gitCmd = &cobra.Command{
	Use:   "git [repo-path]",
	Short: "Scan git repository history for secrets",
	Args:  cobra.MaximumNArgs(1),
	RunE:  runGit,
}

func init() {
	gitCmd.Flags().StringVarP(
		&gitBranch, "branch", "b", "",
		"branch to scan (default: HEAD)",
	)
	gitCmd.Flags().StringVar(
		&gitSince, "since", "",
		"scan commits since date (YYYY-MM-DD)",
	)
	gitCmd.Flags().IntVarP(
		&gitDepth, "depth", "d", 0,
		"max number of commits to scan (0 = all)",
	)
	gitCmd.Flags().BoolVar(
		&stagedOnly, "staged", false,
		"scan only staged changes",
	)
}

func runGit(cmd *cobra.Command, args []string) error {
	path := "."
	if len(args) > 0 {
		path = args[0]
	}

	ui.PrintBanner()

	reg := rules.NewRegistry()
	rules.RegisterBuiltins(reg)
	applyRuleConfig(reg)

	if gitSince == "" && cfg != nil && cfg.Scan.Since != "" {
		gitSince = cfg.Scan.Since
	}
	if gitDepth == 0 && cfg != nil && cfg.Scan.Depth > 0 {
		gitDepth = cfg.Scan.Depth
	}

	src := source.NewGit(
		path, gitBranch, gitSince, gitDepth,
		stagedOnly, maxSize, excludes,
	)

	return executeScan(cmd.Context(), reg, src)
}
