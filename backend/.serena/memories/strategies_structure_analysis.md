# GuruShots Strategies Structure Analysis

## Current strategies.ini Format

### Structure Pattern
```ini
[strategy_name]
description="Description of the strategy"
0="action,timing,parameter"
1="action,timing,parameter"
...
```

### Existing Actions
- **vote**: Execute votes on photos
  - `vote,end-2m0s,80` = Vote 80 times at 2 minutes before end
  - `vote,now,70` = Vote 70 times now
  - `vote,next-1m0s,1` = Vote 1 time in 1 minute

### Timing Formats
- **end-XmYs**: X minutes Y seconds before challenge end
  - `end-4m0s` = 4 minutes before end
  - `end-0m30s` = 30 seconds before end
- **now**: Execute immediately
- **next-XmYs**: In X minutes Y seconds from now
  - `next-1m0s` = in 1 minute

## Proposed Extensions for ANCA Strategies

### New Actions
1. **submit**: Submit/enter photo to challenge
   - `submit,end-60m0s,image-id` = Submit photo at 60min before end
   - `submit,end-24h0m0s,image-id` = Submit 24 hours before end

2. **swap**: Swap photos in challenge  
   - `swap,end-55m0s,current-id,new-id` = Swap photos at 55min before end
   - `swap,end-3h0m0s,slot-1,new-image` = Swap slot 1 at 3h before end

3. **boost**: Activate boost on photo
   - `boost,end-5m0s,image-id` = Boost photo at 5min before end
   - `boost,end-1h0m0s,image-id` = Boost 1 hour before end

4. **turbo**: Activate turbo
   - `turbo,end-1h0m0s,algorithm` = Use turbo algorithm in last hour

5. **fill**: Fill vote meter to specific level
   - `fill,end-12h0s,100` = Fill to 100% at 12h before end

## ANCA Strategy Examples

### 4-Image Challenge Strategy
```ini
[anca_4images]
description="ANCA 4-image strategy - empty slots + 12h boost window"
0="submit,end-24h0m0s,starter-image"
1="boost,end-12h0m0s,starter-image"  # 5min boost window
2="swap,end-12h0m5s,starter-image,boosted-image"  # Remove after boost
3="submit,end-12h0m0s,final-image"    # Add back boosted image
4="fill,end-1h0m0s,100"               # Fill meter last hour
5="turbo,end-1h0m0s,default"          # Turbo last hour
```

### Single Challenge Strategy  
```ini
[anca_single]
description="ANCA single strategy - 24h entry + 3h swap + 1h turbo"
0="submit,end-24h0m0s,initial-image"
1="swap,end-3h0m0s,initial-image,final-image"
2="fill,end-1h0m0s,100"
3="turbo,end-1h0m0s,default"
```

## Implementation Notes
- All image-id parameters need to be resolved from user's photo gallery
- Timing needs to be calculated dynamically based on challenge end time
- Actions should support conditional execution (e.g., only if not already submitted)
- Error handling for API failures and retries