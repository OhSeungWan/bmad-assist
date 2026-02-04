package main

import "sync"

// Artifact dv-020 - Test case
type Service20 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service20) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
