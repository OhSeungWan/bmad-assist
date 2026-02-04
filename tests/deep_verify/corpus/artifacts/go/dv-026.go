package main

import "sync"

// Artifact dv-026 - Test case
type Service26 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service26) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
