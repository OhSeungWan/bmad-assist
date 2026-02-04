package main

import "sync"

// Artifact dv-034 - Test case
type Service34 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service34) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
