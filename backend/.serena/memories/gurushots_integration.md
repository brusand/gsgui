# GSGUI Backend - GuruShots Integration and Strategies

## Implemented GuruShots API Functions

### Core Functions Available
1. **Voting System**
   - `submit_votes()`: Submit multiple votes in a challenge
   - `execute_simple_vote()`: Simple automated voting with specified count
   - `get_vote_panel()`: Retrieve photos to vote on

2. **Challenge Management**  
   - `get_challenges()`: Retrieve active challenges
   - Challenge data parsing and analysis

3. **Turbo System**
   - `execute_turbo()`: Execute turbo boost with sophisticated algorithms
   - `execute_turbo_challenge()`: Turbo execution for specific challenges  
   - Turbo history tracking and status management

## Strategy Implementation Opportunities

Based on the ANCA strategy document, here are automation opportunities:

### Timing Strategies
- **Entry Timing**: Automate when to enter challenges (24h before end, 12h, 3h, etc.)
- **Slot Management**: Keep slots empty until optimal timing
- **Boost Windows**: 5-minute boost windows with immediate withdrawal
- **Premium Hours**: 12-hour and 2-hour windows before challenge end

### Photo Management  
- **Swap Timing**: Automated photo swapping at strategic moments
- **Meter Filling**: Automatic vote meter management
- **Image Selection**: Landscape vs vertical format validation

### Competitor Tracking
- **Following Integration**: Track competitor behavior (like ANCA the vampire)
- **Pattern Recognition**: Learn from successful player strategies  
- **Adaptive Timing**: Adjust strategy based on competitor actions

### Current Implementation Status
- ✅ **Basic Voting**: Implemented via `execute_simple_vote()`
- ✅ **Fill Functionality**: Vote submission with meter management  
- ✅ **Turbo Unlocking**: Advanced turbo algorithms implemented
- ⚠️ **Swap/RetroSwap**: Mentioned as implemented in previous project
- 🔄 **Strategy Scheduling**: Framework exists, needs ANCA strategies integration
- 📋 **Competitor Tracking**: Previous implementation existed, needs restoration

## Integration Points for Advanced Strategies

### Data Sources Needed
- Challenge timing data
- Competitor activity tracking  
- Photo performance metrics
- Historical success patterns

### Automation Opportunities  
1. **Challenge Entry Automation**: Based on timing rules
2. **Vote Distribution**: Strategic voting based on meter status
3. **Turbo Timing**: Last-hour turbo deployment
4. **Photo Rotation**: Automated swap/retroswap cycles

### File-Based Configuration
The system uses `.ini` files for persistence:
- `strategies.ini`: Strategy configurations
- `gsgui.ini`: User profiles and challenge history  
- Maintains compatibility with original `gsui.py` implementation