package main

import "sync"

// Counter has a race condition
type Counter struct {
    mu    sync.Mutex
    count int
}

// Race condition: check-then-act
func (c *Counter) IncrementIfPositive() {
    if c.count >= 0 {
        c.count++
    }
}
