package main

import "sync"

// Artifact dv-022 - Test case
type Service22 struct {
    mu sync.Mutex
    data map[string]string
}

func (s *Service22) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}
