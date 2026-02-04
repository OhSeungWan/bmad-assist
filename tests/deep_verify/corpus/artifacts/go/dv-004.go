package main

import (
	"context"
	"time"
)

// MessageQueue represents a simple message queue
type MessageQueue struct {
	messages chan string
	done     chan struct{}
}

// NewMessageQueue creates a new message queue
func NewMessageQueue(size int) *MessageQueue {
	return &MessageQueue{
		messages: make(chan string, size),
		done:     make(chan struct{}),
	}
}

// Publish sends a message to the queue
// VULNERABILITY: No timeout handling (CC-002 potential)
func (mq *MessageQueue) Publish(msg string) error {
	mq.messages <- msg
	return nil
}

// Consume consumes messages with timeout issues
// VULNERABILITY: Context timeout not properly checked
func (mq *MessageQueue) Consume(ctx context.Context) (string, error) {
	select {
	case msg := <-mq.messages:
		return msg, nil
	case <-time.After(30 * time.Second):  // Fixed timeout, not from context
		return "", context.DeadlineExceeded
	}
}
