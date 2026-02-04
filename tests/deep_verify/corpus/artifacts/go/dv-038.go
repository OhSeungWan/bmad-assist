package main

import "sync"

// Artifact dv-038 - Test case
type Service38 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service38) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
