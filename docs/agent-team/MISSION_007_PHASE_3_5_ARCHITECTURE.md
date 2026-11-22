# MISSÃO 007 — FASE 3.5 WEBSOCKET ARCHITECTURE
## Real-Time Updates for Command Center

**Date:** 2026-11-22  
**Checkpoint:** `298cb54`  
**Status:** 📐 **ETAPA 1 - ARCHITECTURE DESIGN**

---

## ARCHITECTURAL DESIGN

### 1. WebSocket Endpoint Design

#### Endpoint: `/api/v1/ws`

**Connection Handshake:**
```
Client connects: ws://localhost:8000/api/v1/ws?token=JWT_TOKEN

Server validates:
1. Query parameter: token (JWT Bearer token)
2. Token validation: decode and verify signature
3. Extract identity: user_id, tenant_id, actor_id, actor_role
4. Validate: tenant_id MUST exist and match JWT claims
5. Accept or reject connection based on auth result
```

**Authentication Flow:**
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ ws://host/api/v1/ws?token=JWT
       ↓
┌──────────────────────────────┐
│  WebSocket Handshake Middleware   │
├──────────────────────────────┤
│ 1. Extract token from query  │
│ 2. Decode JWT                │
│ 3. Validate signature        │
│ 4. Extract identity          │
│ 5. Check tenant_id validity  │
└──────┬───────────────────────┘
       │
       ├─→ Valid: Accept connection
       │   └─→ Store: (connection_id, tenant_id, user_id)
       │
       └─→ Invalid: Reject with 403 Forbidden
```

**Key Security Rule:**
- ✅ Tenant_id from JWT ONLY
- ❌ NEVER from query parameters
- ❌ NEVER from message body
- ❌ NEVER infer or assume tenant

---

### 2. Connection Management

**Connection State Machine:**
```
                CONNECTING
                    ↓
            (auth validation)
                    ↓
        ✓ → AUTHENTICATED → READY ← ✗ → DISCONNECTED
                            ↓
                       (heartbeat)
                            ↓
                        ACTIVE
                            ↓
                   (subscription/events)
                            ↓
                       (disconnect/timeout)
                            ↓
                       DISCONNECTED
```

**Connection Registry:**
```python
class ConnectionManager:
    """Manage active WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[str, ClientConnection] = {}
        # Key: connection_id (UUID)
        # Value: ClientConnection(websocket, tenant_id, user_id, subscriptions, cursor)
    
    async def connect(self, connection_id: str, ws: WebSocket, identity: Identity):
        """Accept new connection with identity."""
        client = ClientConnection(
            connection_id=connection_id,
            websocket=ws,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            actor_id=identity.actor_id,
            subscriptions=set(),  # Event types subscribed to
            cursor=None,  # For event recovery
        )
        self.active_connections[connection_id] = client
    
    async def disconnect(self, connection_id: str):
        """Remove connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
    
    async def broadcast_to_tenant(self, tenant_id: str, event: Event):
        """Send event to all connections for this tenant."""
        for conn in self.active_connections.values():
            if conn.tenant_id == tenant_id:
                if event.type in conn.subscriptions:
                    await conn.send_json(event.dict())
```

---

### 3. Event Subscription Model

**Subscription Request:**
```json
{
  "action": "subscribe",
  "event_types": [
    "mission.updated",
    "task.updated",
    "execution.completed"
  ]
}
```

**Subscription Response:**
```json
{
  "action": "subscribed",
  "event_types": ["mission.updated", "task.updated", "execution.completed"],
  "status": "ok"
}
```

**Unsubscribe Request:**
```json
{
  "action": "unsubscribe",
  "event_types": ["mission.updated"]
}
```

**Available Event Types:**
```
mission.created
mission.updated
mission.completed
mission.failed

task.created
task.assigned
task.updated
task.completed
task.failed

execution.requested
execution.started
execution.updated
execution.completed
execution.failed

validation.requested
validation.completed

agent.status_changed

projection.updated (Projection Worker checkpoint)
```

**Multi-Tenant Rule:**
- ✅ Client receives ONLY events for their tenant
- ✅ Server filters by tenant_id before sending
- ❌ No cross-tenant event leakage possible

---

### 4. Event Message Format

**Incoming Event to Client:**
```json
{
  "type": "event",
  "event_id": "evt_12345",
  "event_type": "mission.updated",
  "mission_id": "mission_001",
  "tenant_id": "tenant_123",
  "timestamp": "2026-11-22T10:30:00Z",
  "sequence": 42,
  "payload": {
    "mission_id": "mission_001",
    "status": "RUNNING",
    "progress": 65
  }
}
```

**Heartbeat Message (Server → Client):**
```json
{
  "type": "heartbeat",
  "timestamp": "2026-11-22T10:30:30Z",
  "cursor": 42
}
```

**Heartbeat Interval:** 30 seconds  
**Heartbeat Timeout:** 60 seconds (disconnect if no heartbeat)

---

### 5. Reconnection & Recovery

**Reconnection with Cursor:**
```json
{
  "action": "reconnect",
  "cursor": 42,
  "event_types": ["mission.updated", "task.updated"]
}
```

**Server Recovery Response:**
```json
{
  "action": "reconnected",
  "status": "ok",
  "cursor": 42,
  "missed_events": [
    { "event_id": "evt_43", "sequence": 43, "type": "mission.updated" },
    { "event_id": "evt_44", "sequence": 44, "type": "task.updated" }
  ]
}
```

**Recovery Strategy:**
- ✅ Maintain event cursor (last received sequence number)
- ✅ Store events in PostgreSQL event_log table (temporary)
- ✅ Retrieve missed events on reconnection
- ✅ Send missed events before resuming normal stream
- ✅ Discard events older than 24 hours

**Event Log Table:**
```sql
CREATE TABLE websocket_event_log (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE,
    event_type VARCHAR(32),
    tenant_id VARCHAR(64),
    sequence BIGINT,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    INDEX (tenant_id, sequence),
    INDEX (created_at)  -- For cleanup
);
```

---

### 6. Backpressure Handling

**Client-Side Backpressure:**
```python
class ClientConnection:
    async def send_json(self, data: dict):
        """Send JSON with backpressure handling."""
        try:
            if self.pending_messages > MAX_PENDING:
                # Queue full, skip event (not critical for real-time)
                return
            await self.websocket.send_json(data)
            self.pending_messages += 1
        except WebSocketDisconnected:
            # Connection lost, will cleanup on next heartbeat timeout
            pass
```

**Server-Side Backpressure:**
- ✅ Limit message queue per connection (1000 messages)
- ✅ Discard oldest messages if queue full
- ✅ Log warning for backpressure events
- ✅ Trigger reconnection logic on client

---

### 7. Error Handling

**Error Message Format:**
```json
{
  "type": "error",
  "code": "AUTH_EXPIRED",
  "message": "Token expired. Please reconnect.",
  "action": "reconnect"
}
```

**Error Types:**
- `AUTH_EXPIRED` - Token expired, reconnect required
- `AUTH_INVALID` - Invalid token, reconnect with new token
- `SUBSCRIPTION_ERROR` - Invalid event type requested
- `BACKPRESSURE` - Server too busy, slow down requests
- `INTERNAL_ERROR` - Unexpected server error

---

### 8. Security Validation

**Tenant Validation Checklist:**
```
On each message received:
✅ 1. Connection authenticated? (JWT valid at handshake)
✅ 2. Connection still active? (not stale)
✅ 3. Tenant_id in connection matches identity?
✅ 4. Event's tenant_id = connection's tenant_id?
✅ 5. User authorized for this event type? (can subscribe)

On each event sent to client:
✅ 1. Event's tenant_id = client's tenant_id?
✅ 2. No cross-tenant data in payload?
✅ 3. No sensitive fields exposed?
✅ 4. Client subscribed to event_type?
```

**Rule Violations:**
- ❌ Mismatch in tenant_id → Log security incident, disconnect
- ❌ Unauthorized event type → Reject subscription, log warning
- ❌ Token expired → Disconnect, require new connection

---

## ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATIONS                       │
│  (JavaScript, Python, Go clients with auto-reconnect)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                    WebSocket
                   /api/v1/ws
                    (JWT auth)
                         │
         ┌───────────────┴───────────────┐
         ↓                               ↓
┌─────────────────────────────┐  ┌──────────────────────┐
│   WebSocket Manager         │  │  Connection Registry │
│  (async message routing)    │  │  (tenant isolation)  │
└────────────┬────────────────┘  └──────────────────────┘
             │
      ┌──────┴──────┐
      ↓             ↓
┌──────────────┐  ┌──────────────────┐
│ PostgreSQL   │  │ Event Bus SQLite │
│ (read cache) │  │ (source of truth)│
└──────────────┘  └──────────────────┘
      │                     │
      ├─→ Subscription filter
      │   (tenant validation)
      │
      ↓
┌─────────────────────────────┐
│   Real-Time Event Stream    │
│  (filtered by tenant)       │
└─────────────────────────────┘
      │
      ↓ (send to client via WebSocket)
┌─────────────────────────────┐
│   Client Receives Events    │
│   (Reconstruct UI state)    │
└─────────────────────────────┘
```

---

## DATA FLOW EXAMPLE

**Scenario: Mission status update in real-time**

```
1. Event Bus receives: MissionUpdated(mission_001, status=RUNNING)
   
2. Projection Worker:
   - Consumes event from SQLite
   - Updates PostgreSQL: missions.status = RUNNING
   - Logs to websocket_event_log (sequence=42)

3. WebSocket Manager:
   - Polls websocket_event_log for new events
   - Checks subscriptions: mission.updated
   - Finds connections with tenant_id=mission.tenant_id
   - For each subscribed connection:
     * Check client subscribed to mission.updated ✓
     * Check event's tenant matches connection's tenant ✓
     * Send event JSON to client

4. Client:
   - Receives event via WebSocket
   - Updates local UI: Mission status → RUNNING
   - Stores cursor=42 for recovery
```

---

## NEXT STEPS

**ETAPA 2:** Event Subscription API Implementation
- Python/FastAPI WebSocket handler
- Connection manager
- Tenant validation middleware
- Event routing logic

**Expected Duration:** 2-3 hours

---

**Architecture Design Complete:** 2026-11-22  
**Status:** 🟢 **ETAPA 1 COMPLETE - READY FOR IMPLEMENTATION**  
**Next:** ETAPA 2 (Event Subscription API)
