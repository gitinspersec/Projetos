/*
©AngelaMos | 2026
writer.go

In-place updater for requirements.txt that preserves comments and original casing

Matches package names in PEP 503 normalized form while keeping the original
capitalization in the file. Writes atomically via temp file and rename.

Key exports:
  UpdateFile - replaces version specifiers for the given packages in a requirements.txt

Connects to:
  update.go       - called when the target file ends in .txt
  pypi/client.go  - imports NormalizeName for case-insensitive name matching
*/

package requirements

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/CarterPerez-dev/angela/internal/pypi"
)

// UpdateFile replaces version specifiers for the given packages in a
// requirements.txt file, preserving all comments and formatting
func UpdateFile(path string, updates map[string]string) error {
	data, err := os.ReadFile(path) //nolint:gosec
	if err != nil {
		return fmt.Errorf("read %s: %w", path, err)
	}

	content := data
	for pkg, spec := range updates {
		pattern := buildPattern(pkg)
		found := false
		content = pattern.ReplaceAllFunc(
			content,
			func(match []byte) []byte {
				found = true
				return replaceSpec(pattern, match, spec)
			},
		)
		if !found {
			return fmt.Errorf(
				"dependency %q not found in %s", pkg, path,
			)
		}
	}

	path = filepath.Clean(path)
	tmp := path + ".tmp"
	//nolint:gosec // path sanitized via filepath.Clean
	if err := os.WriteFile(tmp, content, 0o600); err != nil {
		return fmt.Errorf("write temp: %w", err)
	}
	if err := os.Rename(tmp, path); err != nil {
		_ = os.Remove(tmp) //nolint:errcheck
		return fmt.Errorf("rename: %w", err)
	}
	return nil
}

func buildPattern(name string) *regexp.Regexp {
	normalized := pypi.NormalizeName(name)
	parts := strings.Split(normalized, "-")
	for i, p := range parts {
		parts[i] = regexp.QuoteMeta(p)
	}
	namePattern := strings.Join(parts, `[-_.]?`)

	return regexp.MustCompile(
		`(?im)^(` + namePattern + `)` +
			`(\[[^\]]*\])?` +
			`(\s*[><=!~][^\n;#]*)`,
	)
}

func replaceSpec(
	re *regexp.Regexp, match []byte, newSpec string,
) []byte {
	groups := re.FindSubmatch(match)
	if len(groups) < 4 {
		return match
	}

	var b []byte
	b = append(b, groups[1]...)
	b = append(b, groups[2]...)
	b = append(b, []byte(newSpec)...)
	return b
}
