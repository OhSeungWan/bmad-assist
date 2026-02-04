package main

import "sync"

// Artifact dv-018 - Test case
type Service18 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service18) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
