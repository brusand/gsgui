# ANCA Surveillance Implementation - Simplified Version

## Overview
Simplified ANCA surveillance system using existing methods + Cron MCP, without complex infrastructure.

## Key Components

### 1. Simple ANCA Surveillance (`simple_anca_surveillance.py`)
- **Uses existing methods**: get_top_photographer(), get_challenges()
- **Cron MCP integration**: Called every 10 minutes via cron job
- **Event detection**: Compares current vs previous states
- **JSON storage**: Persists events in anca_surveillance_data.json
- **WebSocket notifications**: Real-time alerts for ANCA activity

### 2. Extended Strategy Executor (`extended_strategy_executor.py`)  
- **Reads strategies.ini**: Supports [4photos] format with new actions
- **New actions supported**:
  - `submit,end-120m0s,image-id` - Submit photo at timing
  - `swap,end-90m0s,old-id,new-id` - Swap photos strategically
  - `boost,end-50m0s,0` - Boost photo (index 0 = most votes)
  - `turbo,end-50m0s,1` - Unlock turbo via set_turbo API
  - `vote,end-2m0s,80` - Vote (existing, maintained)
- **Timing calculation**: Precise scheduling relative to challenge end
- **Async execution**: Non-blocking strategy execution with WebSocket updates

### 3. API Endpoints (`simple_extensions.py`)
- `POST /simple/anca/surveillance/run` - Manual surveillance run
- `GET /simple/anca/events` - Get ANCA events
- `GET /simple/anca/stats` - Surveillance statistics
- `POST /simple/strategies/extended/execute` - Execute [4photos] strategy
- `GET /simple/strategies/extended/{id}/status` - Strategy status
- `POST /simple/cron/anca-surveillance` - Cron job endpoint

## Example [4photos] Strategy

```ini
[4photos]
description="Stratégie 4 photos ANCA-style"
0=submit, end-120m0s, 83a85db59ad25b9e9171781de48d123b
1=vote, end-120m0s, 80
2=swap, end-90m0s, 83a85db59ad25b9e9171781de48d123b, 83a85db59ad25b9e9171781de48d134332
3=swap, end-60m0s, 83a85db59ad25b9e9171781de48d134332, 83a85db59ad25b9e9171781de48d123b
4=submit, end-60m0s, 83a85db59ad25b9e9171781de48d122323, 83a85db59ad25b9e9171781de48d12324, 83a85db59ad25b9e9171781de48d12325
5=vote, end-60m0s, 80
6=boost, end-50m0s, 0    # [0] = photo with most votes
7=turbo, end-50m0s, 1    # [1] = second photo
8=vote, end-2m0s, 80
9=vote, end-0m45s, 20
```

## Required API Methods
System uses these methods from GuruShotsAPI:

### Existing Methods Used
- `get_challenges()` - List active challenges
- `get_challenge_followings(challenge_id)` - Get ranking (uses get_top_photographer)
- `execute_simple_vote(challenge_url, count)` - Vote functionality
- `swap_photo(challenge_id, current_id, new_id)` - Photo swapping

### New Methods Required
- `submit_to_challenge(challenge_id, image_id)` - Submit photo
- `boost_photo(challenge_id, image_id)` - Boost photo  
- `set_turbo(challenge_id)` - Unlock turbo (NOT turbo_executor)

## Cron MCP Integration

```python
@cron("*/10 * * * *")  # Every 10 minutes
async def anca_surveillance_job():
    response = requests.post("http://localhost:8000/api/v1/simple/cron/anca-surveillance")
    results = response.json()
```

## Data Storage
- **anca_surveillance_data.json**: All ANCA events with timestamps
- **strategies.ini**: Strategy configurations (read-only)
- **WebSocket events**: Real-time notifications

## Event Types Detected
- **new_entry**: ANCA posts new photo
- **swap_out**: ANCA removes photo (key indicator)
- **rank_change**: Significant ranking changes (±10 positions)
- **first_detection**: First time seeing ANCA in challenge

## Integration Points
- **Existing StrategyScheduler**: Remains unchanged for simple strategies
- **Extended strategies**: New system for complex multi-action strategies
- **WebSocket system**: Reuses existing notification infrastructure
- **Config system**: Compatible with existing user/profile management

## Advantages of Simplified Approach
- **Uses existing methods**: No complex new API integrations
- **Cron MCP integration**: Leverages your existing cron system
- **Minimal infrastructure**: JSON storage instead of complex databases
- **Backwards compatible**: Doesn't break existing functionality
- **Easy debugging**: Simple, traceable execution flow