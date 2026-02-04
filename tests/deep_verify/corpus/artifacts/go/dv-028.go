package main

import "sync"

// Artifact dv-028 - Test case
type Service28 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service28) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
