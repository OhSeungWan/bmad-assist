package main

import "sync"

// Artifact dv-016 - Test case
type Service16 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service16) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
