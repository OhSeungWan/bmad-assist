package main

import "sync"

// Artifact dv-030 - Test case
type Service30 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service30) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
