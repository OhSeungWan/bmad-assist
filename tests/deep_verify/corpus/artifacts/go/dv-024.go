package main

import "sync"

// Artifact dv-024 - Test case
type Service24 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service24) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
