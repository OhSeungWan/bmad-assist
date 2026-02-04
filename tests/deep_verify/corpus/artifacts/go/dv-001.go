package main

import (
	"sync"
)

// Buffer represents a thread-safe buffer with a race condition
// This demonstrates CC-004: Check-then-act race condition
type Buffer struct {
	mu   sync.Mutex
	data []int
}

// Add adds an item to the buffer
// VULNERABILITY: Check-then-act race condition (CC-004)
func (b *Buffer) Add(item int) {
	b.mu.Lock()
	defer b.mu.Unlock()

	// This looks protected, but demonstrates the pattern
	if len(b.data) > 0 {
		b.data = append(b.data, item)
	}
}

// UnsafeAdd has a clear race condition
// VULNERABILITY: Check-then-act without lock (CC-004)
func (b *Buffer) UnsafeAdd(item int) {
	if len(b.data) < 100 {
		b.data = append(b.data, item)
	}
}
