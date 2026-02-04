package main

import "sync"

// Artifact dv-032 - Test case
type Service32 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service32) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
