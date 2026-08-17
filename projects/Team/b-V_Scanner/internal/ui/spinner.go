/*
©AngelaMos | 2026
spinner.go

Goroutine-backed terminal spinner with graceful stop

Renders a braille-frame animation while API calls run in the background.
Hides the cursor on start, clears the line on stop, and uses a WaitGroup
to block until the background goroutine exits cleanly before returning.

Key exports:
  Spinner    - spinner struct with Start() and Stop() methods
  NewSpinner - creates a spinner with the given status message

Connects to:
  update.go - creates a spinner before PyPI and OSV API calls
  color.go  - uses CyanBold and HiMagenta for frame and message styling
*/

package ui

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

var frames = []string{
	"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏",
}

type Spinner struct {
	msg    string
	done   chan struct{}
	wg     sync.WaitGroup
	mu     sync.Mutex
	active bool
}

func NewSpinner(msg string) *Spinner {
	return &Spinner{msg: msg}
}

func (s *Spinner) Start() {
	s.mu.Lock()
	if s.active {
		s.mu.Unlock()
		return
	}
	s.active = true
	s.done = make(chan struct{})
	s.wg.Add(1)
	s.mu.Unlock()

	go s.run()
}

func (s *Spinner) Stop() {
	s.mu.Lock()
	if !s.active {
		s.mu.Unlock()
		return
	}
	s.active = false
	close(s.done)
	s.mu.Unlock()
	s.wg.Wait()
}

func (s *Spinner) run() {
	defer s.wg.Done()
	fmt.Print("\033[?25l")

	ticker := time.NewTicker(80 * time.Millisecond)
	defer ticker.Stop()

	idx := 0
	for {
		select {
		case <-s.done:
			clearLine()
			fmt.Print("\033[?25h")
			return
		case <-ticker.C:
			frame := frames[idx%len(frames)]
			fmt.Printf(
				"\r  %s %s",
				CyanBold(frame),
				HiMagenta(s.msg),
			)
			idx++
		}
	}
}

func clearLine() {
	fmt.Print("\r" + strings.Repeat(" ", 80) + "\r")
}
