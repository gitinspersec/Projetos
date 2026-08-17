/*
©AngelaMos | 2026
scan.go

"scan" subcommand and shared scan execution logic

Implements "portia scan [path]" for directory scanning and provides
executeScan() which both scan and git commands use. Spins up the pipeline,
optionally checks findings against HIBP (generic-password and generic-secret
rules only), picks the reporter, and writes output to stdout.

Key exports:
  executeScan - shared scan driver called by runScan and runGit
  checkHIBP - annotates generic-password/secret findings with breach data
  applyRuleConfig - applies cfg.Rules.Disable to the rule registry

Connects to:
  cli/root.go - registered as scanCmd, reads global flags
  cli/git.go - calls executeScan() and applyRuleConfig()
  engine/pipeline.go - creates and runs Pipeline
  hibp/client.go - creates Client and calls Check() for HIBP verification
  reporter/reporter.go - calls New(format) and Report()
  source/directory.go - constructs NewDirectory() source
*/

package cli

import (
	"context"
	"os"
	"time"

	"github.com/spf13/cobra"

	"github.com/CarterPerez-dev/portia/internal/engine"
	"github.com/CarterPerez-dev/portia/internal/hibp"
	"github.com/CarterPerez-dev/portia/internal/reporter"
	"github.com/CarterPerez-dev/portia/internal/rules"
	"github.com/CarterPerez-dev/portia/internal/source"
	"github.com/CarterPerez-dev/portia/internal/ui"
	"github.com/CarterPerez-dev/portia/pkg/types"
)

var scanCmd = &cobra.Command{
	Use:   "scan [path]",
	Short: "Scan a directory for secrets",
	Args:  cobra.MaximumNArgs(1),
	RunE:  runScan,
}

func runScan(cmd *cobra.Command, args []string) error {
	path := "."
	if len(args) > 0 {
		path = args[0]
	}

	ui.PrintBanner()

	reg := rules.NewRegistry()
	rules.RegisterBuiltins(reg)
	applyRuleConfig(reg)

	src := source.NewDirectory(path, maxSize, excludes)

	return executeScan(cmd.Context(), reg, src)
}

func executeScan(
	ctx context.Context,
	reg *rules.Registry,
	src source.Source,
) error {
	spin := ui.NewSpinner("Scanning for secrets...")
	if !verbose {
		spin.Start()
	}

	start := time.Now()
	p := engine.NewPipeline(reg)
	p.SetVerbose(verbose)
	result, err := p.Run(ctx, src)
	spin.Stop()

	if err != nil {
		return err
	}

	result.Duration = time.Since(start)

	if enableHIBP && len(result.Findings) > 0 {
		checkHIBP(ctx, result)
	}

	rep := reporter.New(format)
	return rep.Report(os.Stdout, result)
}

func checkHIBP(ctx context.Context, result *types.ScanResult) {
	client := hibp.NewClient()
	spin := ui.NewSpinner("Checking HIBP breach database...")
	spin.Start()
	defer spin.Stop()

	for i := range result.Findings {
		f := &result.Findings[i]
		if f.Secret == "" {
			continue
		}

		if f.RuleID != "generic-password" &&
			f.RuleID != "generic-secret" {
			f.HIBPStatus = types.HIBPSkipped
			continue
		}

		res, err := client.Check(ctx, f.Secret)
		result.HIBPChecked++

		if err != nil {
			f.HIBPStatus = types.HIBPError
			continue
		}

		if res.Breached {
			f.HIBPStatus = types.HIBPBreached
			f.BreachCount = res.Count
			result.HIBPBreached++
		} else {
			f.HIBPStatus = types.HIBPClean
		}
	}
}

func applyRuleConfig(reg *rules.Registry) {
	if cfg == nil {
		return
	}
	if len(cfg.Rules.Disable) > 0 {
		reg.Disable(cfg.Rules.Disable...)
	}
}
