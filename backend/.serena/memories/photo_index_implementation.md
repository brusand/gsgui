# Photo Index Resolution - Complete Implementation

## Implementation Status
✅ **COMPLETED** - Photo index resolution [0], [1], [2] fully implemented and tested

## Core Functionality

### Index Format Support
- `[0]` or `0` = Photo with most votes (highest vote count)
- `[1]` or `1` = Photo with second most votes  
- `[2]` or `2` = Photo with third most votes
- Direct photo IDs still supported: `boost,end-50m0s,abc123`

### Resolution Process
1. **User Identification**: `get_current_user_info()` via GuruShots API
2. **Challenge Ranking**: `get_challenge_followings()` to find user's photos
3. **Vote Sorting**: Sort user's photos by votes (descending order)
4. **Index Mapping**: Return photo ID at requested index position

### Enhanced Strategy Actions

#### Boost with Index
```ini
6=boost, end-50m0s, 0     # Boost photo with most votes [0]
6=boost, end-50m0s, [1]   # Boost second photo by votes [1]
6=boost, end-50m0s, photo_id  # Direct photo ID still works
```

#### Turbo with Index
```ini
7=turbo, end-50m0s, 1     # Turbo targeting second photo [1]
7=turbo, end-50m0s, [0]   # Turbo targeting photo with most votes [0]
```

## New API Methods

### GuruShotsAPI.get_current_user_info()
```python
user_info = await api_client.get_current_user_info()
# Returns: {'user_id': 123, 'username': 'bruno', 'name': 'Bruno'}
```

### ExtendedStrategyExecutor.test_photo_index_resolution()
```python
result = await executor.test_photo_index_resolution(profile_id, challenge_id)
# Returns detailed mapping of [0], [1], [2] to actual photo IDs with votes
```

## Debug Endpoints

### Test Index Resolution
- `POST /simple/strategies/test-photo-index` - Test photo index mapping
- `GET /simple/strategies/debug/photo-indices/{profile_id}/{challenge_id}` - Debug view

### Response Format
```json
{
  "success": true,
  "photos": [
    {"index": 0, "photo_id": "abc123", "votes": 200},
    {"index": 1, "photo_id": "def456", "votes": 150}
  ],
  "index_explanation": {
    "[0]": "Photo with most votes: abc123 (200 votes)",
    "[1]": "Photo with second most votes: def456 (150 votes)"
  }
}
```

## Error Handling
- **User not in challenge**: Clear error message
- **Index out of range**: Shows available indices (0 to N-1)
- **No photos submitted**: Informative error
- **API failures**: Graceful fallback with logs

## Strategy Example with Indices
```ini
[4photos_enhanced]
0=submit, end-120m0s, photo_id_1
1=vote, end-120m0s, 80
2=swap, end-90m0s, photo_id_1, photo_id_2
3=submit, end-60m0s, photo_id_3, photo_id_4
4=boost, end-50m0s, 0        # 🎯 Auto-boost photo with most votes
5=turbo, end-50m0s, 1        # 🎯 Turbo targeting second photo
6=vote, end-2m0s, 80
```

## Technical Implementation
- **Real-time resolution**: Indices resolved at execution time
- **Vote-based sorting**: Always current vote counts
- **Comprehensive logging**: All resolutions logged with details
- **WebSocket updates**: Real-time notifications with resolved photo IDs
- **Backwards compatible**: Existing strategies continue to work

## Usage Workflow
1. **Test indices first**: Use debug endpoint to see current mapping
2. **Create strategy**: Use indices in strategies.ini
3. **Execute strategy**: Indices automatically resolved during execution
4. **Monitor progress**: WebSocket updates show which photos were targeted

## Benefits
- **Dynamic targeting**: Always targets highest-performing photos
- **Strategy flexibility**: Same strategy adapts to different photo performance
- **ANCA-style automation**: Implements "boost photo with most votes" patterns
- **Debug capabilities**: Easy to verify index mappings before execution