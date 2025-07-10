package websocket

import (
	"fmt"
	"log"
	"net/url"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type MessageHandler func([]byte)

type Client struct {
	baseURL        string
	conn           *websocket.Conn
	mu             sync.RWMutex
	messageHandler MessageHandler
	done           chan struct{}
	reconnectDelay time.Duration
	maxReconnect   time.Duration
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL:        baseURL,
		reconnectDelay: 1 * time.Second,
		maxReconnect:   30 * time.Second,
		done:           make(chan struct{}),
	}
}

func (c *Client) OnMessage(handler MessageHandler) {
	c.messageHandler = handler
}

func (c *Client) Connect() error {
	// Parse WebSocket URL
	u, err := url.Parse(c.baseURL)
	if err != nil {
		return err
	}
	
	// Change scheme to ws
	if u.Scheme == "http" {
		u.Scheme = "ws"
	} else if u.Scheme == "https" {
		u.Scheme = "wss"
	}
	
	// Add WebSocket path with client ID
	u.Path = "/ws/go-ui-client"
	
	// Connect to WebSocket
	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return fmt.Errorf("failed to connect to WebSocket: %v", err)
	}
	
	c.mu.Lock()
	c.conn = conn
	c.mu.Unlock()
	
	// Start read loop
	go c.readLoop()
	
	// Start reconnect loop
	go c.reconnectLoop()
	
	log.Printf("Connected to WebSocket at %s", u.String())
	return nil
}

func (c *Client) Close() {
	close(c.done)
	
	c.mu.Lock()
	if c.conn != nil {
		c.conn.Close()
	}
	c.mu.Unlock()
}

func (c *Client) Send(message []byte) error {
	c.mu.RLock()
	conn := c.conn
	c.mu.RUnlock()
	
	if conn == nil {
		return fmt.Errorf("not connected")
	}
	
	return conn.WriteMessage(websocket.TextMessage, message)
}

func (c *Client) IsConnected() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.conn != nil
}

func (c *Client) readLoop() {
	for {
		c.mu.RLock()
		conn := c.conn
		c.mu.RUnlock()
		
		if conn == nil {
			return
		}
		
		_, message, err := conn.ReadMessage()
		if err != nil {
			log.Printf("WebSocket read error: %v", err)
			
			c.mu.Lock()
			c.conn = nil
			conn.Close()
			c.mu.Unlock()
			
			return
		}
		
		if c.messageHandler != nil {
			c.messageHandler(message)
		}
	}
}

func (c *Client) reconnectLoop() {
	delay := c.reconnectDelay
	
	for {
		select {
		case <-c.done:
			return
		case <-time.After(delay):
			if !c.IsConnected() {
				log.Println("Attempting to reconnect...")
				if err := c.Connect(); err != nil {
					log.Printf("Reconnect failed: %v", err)
					
					// Exponential backoff
					delay *= 2
					if delay > c.maxReconnect {
						delay = c.maxReconnect
					}
				} else {
					// Reset delay on successful reconnect
					delay = c.reconnectDelay
				}
			}
		}
	}
}