/*
©AngelaMos | 2026
source.go

Source interface for scanner content providers

Defines the Source interface: Chunks sends text chunks on a channel for the
pipeline to consume. The two implementations are Directory (filesystem walk)
and Git (commit history or staged index).

Connects to:
  source/directory.go - implements Source
  source/git.go - implements Source
  engine/pipeline.go - accepts a Source to begin scanning
  cli/scan.go - constructs a Directory source
  cli/git.go - constructs a Git source
*/

package source

import (
	"context"

	"github.com/CarterPerez-dev/portia/pkg/types"
)

type Source interface {
	Chunks(ctx context.Context, out chan<- types.Chunk) error
	String() string
}
