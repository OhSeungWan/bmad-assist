package main

import "sync"

// Artifact dv-040 - Test case
type Service40 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service40) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
