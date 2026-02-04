package main

import "sync"

// Artifact dv-036 - Test case
type Service36 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service36) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
