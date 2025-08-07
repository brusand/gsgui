# Photo Index Resolution - Implementation Complete

## ✅ Implementation Details

### Photo Index Format Supported
- `[0]` or `0` = Photo with most votes
- `[1]` or `1` = Photo with second most votes  
- `[2]` or `2` = Photo with third most votes
- etc.

### Index Resolution Process
1. **Get current user info** via `get_current_user_info()` API call
2. **Find user in challenge ranking** using `get_challenge_followings()`
3. **Sort user's photos by votes** (descending order)
4. **Return photo ID at requested index**

### Enhanced Actions

#### Boost with Index
```ini
# Original format
6=boost, end-50m0s, 0    # Boost photo with most votes

# Also supported
6=boost, end-50m0s, [0]  # Explicit bracket notation
6=boost, end-50m0s, 1    # Boost second photo by votes
6=boost, end-50m0s, photo_id_direct  # Direct photo ID still works
```

#### Turbo with Index
```ini
# Target specific photo for turbo (logged for future enhancement)
7=turbo, end-50m0s, 1    # Turbo targeting second photo
7=turbo, end-50m0s, [0]  # Turbo targeting photo with most votes
```

## 🔧 New API Methods Added

### GuruShotsAPI
```python
await api_client.get_current_user_info()
# Returns: {'user_id': 123, 'username': 'bruno', 'name': 'Bruno', 'profile_url': '...'}
```

### ExtendedStrategyExecutor
```python
# Test photo index resolution
result = await executor.test_photo_index_resolution(profile_id, challenge_id)
# Returns detailed mapping of indices to photos with votes
```

## 📡 Debug Endpoints

### Test Photo Index Resolution
```bash
POST /api/v1/simple/strategies/test-photo-index
{
  "profile_id": "bruno",
  "challenge_id": 12345
}
```

**Response:**
```json
{
  "success": true,
  "user_info": {
    "username": "bruno",
    "user_id": 123,
    "total_rank": 15,
    "total_votes": 450
  },
  "photos": [
    {"index": 0, "photo_id": "photo123", "votes": 200, "boost_status": false},
    {"index": 1, "photo_id": "photo456", "votes": 150, "boost_status": true},
    {"index": 2, "photo_id": "photo789", "votes": 100, "boost_status": false}
  ],
  "index_explanation": {
    "[0]": "Photo with most votes: photo123 (200 votes)",
    "[1]": "Photo with second most votes: photo456 (150 votes)"
  }
}
```

### Debug Photo Indices
```bash
GET /api/v1/simple/strategies/debug/photo-indices/bruno/12345
```

**Response:**
```json
{
  "challenge_id": 12345,
  "user": {"username": "bruno", "total_rank": 15},
  "photo_count": 3,
  "index_mapping": {
    "[0]": {"photo_id": "photo123", "votes": 200, "boost_status": false},
    "[1]": {"photo_id": "photo456", "votes": 150, "boost_status": true}
  },
  "boost_command_examples": {
    "boost,end-50m0s,0": "Boost photo photo123 (200 votes)",
    "boost,end-50m0s,1": "Boost photo photo456 (150 votes)"
  },
  "turbo_command_examples": {
    "turbo,end-50m0s,0": "Turbo targeting photo photo123 (200 votes)",
    "turbo,end-50m0s,1": "Turbo targeting photo photo456 (150 votes)"
  }
}
```

## 🎯 Updated [4photos] Strategy Example

```ini
[4photos_with_indices]
description="Stratégie 4 photos avec résolution d'index automatique"
0=submit, end-120m0s, 83a85db59ad25b9e9171781de48d123b
1=vote, end-120m0s, 80
2=swap, end-90m0s, 83a85db59ad25b9e9171781de48d123b, 83a85db59ad25b9e9171781de48d134332
3=swap, end-60m0s, 83a85db59ad25b9e9171781de48d134332, 83a85db59ad25b9e9171781de48d123b
4=submit, end-60m0s, 83a85db59ad25b9e9171781de48d122323, 83a85db59ad25b9e9171781de48d12324, 83a85db59ad25b9e9171781de48d12325
5=vote, end-60m0s, 80
6=boost, end-50m0s, 0        # 🎯 Auto-boost photo with most votes
7=turbo, end-50m0s, 1        # 🎯 Turbo targeting second photo
8=vote, end-2m0s, 80
9=vote, end-0m45s, 20
```

## 🔍 Index Resolution Logic

### Sorting Criteria
Photos are sorted by **votes (descending)**:
- Index [0] = Photo with highest votes
- Index [1] = Photo with second highest votes
- Index [2] = Photo with third highest votes
- etc.

### Error Handling
- **User not found in challenge**: Returns error
- **Index out of range**: Returns error with available range
- **No photos in challenge**: Returns error  
- **API failures**: Graceful fallback with detailed error messages

### Logging
All index resolutions are logged with details:
```
✅ Resolved index [0] -> photo abc123 with 200 votes
🔍 Resolving photo index [1] for boost action
⚠️ Could not resolve photo index [3], proceeding with general action
```

## 🚀 Usage Examples

### Test Index Resolution First
```bash
# Check which photos correspond to which indices
curl -X GET "http://localhost:8000/api/v1/simple/strategies/debug/photo-indices/bruno/12345"
```

### Execute Strategy with Indices
```bash
curl -X POST http://localhost:8000/api/v1/simple/strategies/extended/execute \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "bruno",
    "challenge_id": "12345",
    "challenge_url": "nature-challenge",
    "strategy_name": "4photos_with_indices"
  }'
```

### Monitor Execution
The strategy will automatically resolve indices and log:
- Which photo ID corresponds to each index
- Success/failure of each boost/turbo action
- Real-time WebSocket updates with resolved photo IDs

## 🔧 Technical Implementation Notes

### Performance
- Index resolution occurs at execution time (not pre-calculated)
- Caches user info during strategy execution
- Handles rate limits gracefully

### Compatibility
- Direct photo IDs still work: `boost,end-50m0s,abc123`
- Bracket notation optional: `[0]` and `0` both work
- Backwards compatible with existing strategies

### Future Enhancements
- Cache photo rankings during strategy execution
- Support for relative indices (e.g., "second from bottom")
- Integration with photo performance predictions
