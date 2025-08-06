# ANCA Intelligence Program - Surveillance and Analysis

## Overview
Dedicated surveillance system for monitoring ANCA the vampire (anca.chilom), the frequent GuruShots winner known for strategic swap timing and challenge dominance.

## Core Components

### 1. ANCA Intelligence Service (`anca_intelligence.py`)
- **Real-time monitoring** of ANCA across active challenges
- **Event detection**: Automatically detects entries, swaps, boosts, rank changes
- **Pattern analysis**: Identifies behavioral patterns and success strategies
- **Data persistence**: Stores all events with timestamps for analysis
- **WebSocket notifications**: Real-time alerts for ANCA activity

### 2. Enhanced Strategy Engine (`enhanced_strategy_engine.py`)
- **Extended strategy format** supporting new actions:
  - `submit,end-60m0s,image-id` - Submit photo at specific timing
  - `swap,end-55m0s,current-id,new-id` - Swap photos strategically  
  - `boost,end-12h0s,image-id` - Activate boost with timing
  - `turbo,end-1h0s,algorithm` - Execute turbo in final hour
  - `fill,end-2h0s,percentage` - Fill vote meter to level
- **Backwards compatible** with existing strategies.ini format
- **Dynamic ANCA strategies**: Auto-generate 4-image and single challenge strategies
- **Precise timing**: Calculate execution times relative to challenge end

### 3. API Endpoints (`anca_strategies.py`)
- `POST /api/v1/anca/surveillance/start` - Start ANCA monitoring
- `GET /api/v1/anca/events` - Retrieve ANCA activity events
- `GET /api/v1/anca/patterns` - Get behavioral pattern analysis
- `POST /api/v1/anca/export` - Export surveillance data
- `POST /api/v1/strategies/execute` - Execute enhanced strategies
- `POST /api/v1/strategies/anca/create` - Create ANCA-style strategies

## Strategic Intelligence Features

### Event Types Detected
- **Entry**: When ANCA enters a challenge with a photo
- **Swap**: When ANCA swaps photos (key strategic indicator)
- **Boost**: When ANCA activates photo boosts
- **Rank Change**: Significant ranking movements (±10 positions)

### Pattern Analysis
- **Swap frequency**: Track how often ANCA swaps photos
- **Timing patterns**: Identify optimal entry and action timings
- **Success correlation**: Link actions to winning outcomes
- **Strategic windows**: Detect time-based behavioral patterns

### ANCA Strategy Templates

#### 4-Image Challenge Strategy
```ini
[anca_4images]
description="ANCA 4-image strategy - empty slots + 12h boost window"
0="submit,end-24h0m0s,starter-image"
1="boost,end-12h0m0s,starter-image"
2="swap,end-12h0m5s,starter-image,boosted-image"
3="submit,end-12h0m0s,final-image"
4="fill,end-1h0m0s,100"
5="turbo,end-1h0m0s,default"
```

#### Single Challenge Strategy
```ini
[anca_single]
description="ANCA single strategy - 24h entry + 3h swap + 1h turbo"
0="submit,end-24h0m0s,initial-image"
1="swap,end-3h0s,initial-image,final-image"
2="fill,end-1h0m0s,100"
3="turbo,end-1h0m0s,default"
```

## Data Storage and Analysis

### Event Data Structure
- Timestamp with precise timing
- Challenge ID and URL
- Event type and photo IDs involved
- Context data (votes, rank, time left)
- Additional metadata for pattern analysis

### Export Capabilities
- JSON export of all surveillance data
- Event timeline analysis
- Pattern confidence scoring
- Strategic insight reports

## Integration Points

### WebSocket Notifications
- `anca_activity` - High-priority ANCA events
- `competitor_event` - General competitor activities  
- `strategy_started/completed` - Enhanced strategy execution updates

### Existing System Compatibility
- Works with current strategies.ini format
- Integrates with existing TurboExecutor
- Compatible with current GuruShotsAPI methods
- Uses established WebSocket notification system

## Usage Example

### Start ANCA Surveillance
```python
# Start monitoring ANCA in all active challenges
POST /api/v1/anca/surveillance/start
{
  "challenge_ids": [12345, 67890]  # optional
}
```

### Execute ANCA Strategy
```python
# Create and execute 4-image ANCA strategy
POST /api/v1/strategies/anca/create
{
  "strategy_type": "4images"
}

POST /api/v1/strategies/execute
{
  "strategy_name": "anca_4images_20250806_143022",
  "challenge_id": 12345,
  "challenge_url": "my-challenge",
  "challenge_end_time": "2025-08-06T18:00:00Z"
}
```

This intelligence system provides comprehensive monitoring and strategic insights based on ANCA's documented winning patterns, enabling users to learn from and adapt proven successful strategies.