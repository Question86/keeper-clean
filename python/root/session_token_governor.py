#!/usr/bin/env python3
"""
SESSION TOKEN GOVERNOR - Emergency Implementation
TASK: TASK_0132 (Quick prototype for immediate use)
PURPOSE: Self-regulate token consumption in active session
"""

class SessionTokenGovernor:
    """Lightweight token governor for immediate deployment."""
    
    def __init__(self, budget=200000):
        self.budget = budget
        self.zones = {
            'SAFE': (0, 0.50),      # 0-50%: Full capability
            'CAUTION': (0.50, 0.75),  # 50-75%: Moderate
            'CONSERVE': (0.75, 0.85), # 75-85%: Minimal
            'CRITICAL': (0.85, 0.95), # 85-95%: Emergency
            'ABORT': (0.95, 1.00)     # 95%+: Stop
        }
    
    def get_zone(self, tokens_used):
        """Determine current budget zone."""
        pct = tokens_used / self.budget
        
        for zone_name, (low, high) in self.zones.items():
            if low <= pct < high:
                return zone_name
        
        return 'ABORT'
    
    def get_strategy(self, tokens_used):
        """Get execution strategy for current zone."""
        zone = self.get_zone(tokens_used)
        
        strategies = {
            'SAFE': {
                'mode': 'FULL',
                'max_response_tokens': 2000,
                'detail_level': 'HIGH',
                'file_read_limit': None,
                'skip_optional': False,
                'advice': 'Full capability - work normally'
            },
            'CAUTION': {
                'mode': 'MODERATE',
                'max_response_tokens': 1000,
                'detail_level': 'MEDIUM',
                'file_read_limit': 100,
                'skip_optional': False,
                'advice': 'Reduce response verbosity, limit file reads'
            },
            'CONSERVE': {
                'mode': 'MINIMAL',
                'max_response_tokens': 500,
                'detail_level': 'LOW',
                'file_read_limit': 50,
                'skip_optional': True,
                'advice': 'Brief responses only, skip exploration'
            },
            'CRITICAL': {
                'mode': 'EMERGENCY',
                'max_response_tokens': 200,
                'detail_level': 'SUMMARY',
                'file_read_limit': 20,
                'skip_optional': True,
                'advice': 'Finalize work immediately, prepare to save state'
            },
            'ABORT': {
                'mode': 'ABORT',
                'max_response_tokens': 100,
                'detail_level': 'NONE',
                'file_read_limit': 0,
                'skip_optional': True,
                'advice': 'STOP WORK - Save state and exit gracefully'
            }
        }
        
        return strategies[zone]
    
    def recommend_action(self, tokens_used, remaining_work=None):
        """Recommend what to do given current token usage."""
        zone = self.get_zone(tokens_used)
        strategy = self.get_strategy(tokens_used)
        remaining = self.budget - tokens_used
        
        print(f"\n{'='*60}")
        print(f"TOKEN BUDGET STATUS")
        print(f"{'='*60}")
        print(f"Used: {tokens_used:,} / {self.budget:,} ({tokens_used/self.budget*100:.1f}%)")
        print(f"Remaining: {remaining:,}")
        print(f"Zone: {zone}")
        print(f"Mode: {strategy['mode']}")
        print(f"\n{strategy['advice']}")
        print(f"{'='*60}\n")
        
        if zone in ['CONSERVE', 'CRITICAL', 'ABORT']:
            print("⚠️ RECOMMENDATIONS:")
            if zone == 'CONSERVE':
                print("  - Keep responses under 500 tokens")
                print("  - Limit file reads (use limit= parameter)")
                print("  - Skip exploratory analysis")
                print("  - Focus on completing current task only")
            elif zone == 'CRITICAL':
                print("  - Finalize current work immediately")
                print("  - Save all state to files")
                print("  - Prepare brief summary")
                print("  - End session after next few turns")
            elif zone == 'ABORT':
                print("  ❌ ABORT MODE - DO NOT CONTINUE WORK")
                print("  - Save critical state NOW")
                print("  - Respond with summary only")
                print("  - Tell user to start fresh session")
            print()
        
        return zone, strategy


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python session_token_governor.py <tokens_used>")
        sys.exit(1)
    
    tokens_used = int(sys.argv[1])
    governor = SessionTokenGovernor()
    zone, strategy = governor.recommend_action(tokens_used)
    
    print(f"Suggested max response: {strategy['max_response_tokens']} tokens")
    print(f"File read limit: {strategy['file_read_limit']}")
