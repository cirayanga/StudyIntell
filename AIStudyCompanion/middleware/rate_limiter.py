import time
import logging
from functools import wraps
from typing import Dict, Any
from collections import defaultdict, deque
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        # Store request timestamps per IP and endpoint
        self.request_history = defaultdict(lambda: defaultdict(deque))
        
        # Rate limit configurations for different services
        self.limits = {
            'assemblyai': {'requests': 10, 'window': 60},      # 10 requests per minute
            'google_tts': {'requests': 50, 'window': 60},      # 50 requests per minute
            'cohere': {'requests': 100, 'window': 60},         # 100 requests per minute
            'together_ai': {'requests': 50, 'window': 60},     # 50 requests per minute
            'general': {'requests': 100, 'window': 60}         # General API limit
        }
    
    def is_rate_limited(self, identifier: str, service: str = 'general') -> Dict[str, Any]:
        """Check if a request should be rate limited"""
        current_time = time.time()
        
        # Get rate limit configuration for service
        config = self.limits.get(service, self.limits['general'])
        max_requests = config['requests']
        window_size = config['window']
        
        # Get request history for this identifier and service
        requests = self.request_history[identifier][service]
        
        # Remove old requests outside the window
        while requests and requests[0] <= current_time - window_size:
            requests.popleft()
        
        # Check if rate limit is exceeded
        if len(requests) >= max_requests:
            # Calculate when the rate limit will reset
            reset_time = requests[0] + window_size
            return {
                'is_limited': True,
                'reset_time': reset_time,
                'remaining_requests': 0,
                'retry_after': reset_time - current_time
            }
        
        # Add current request to history
        requests.append(current_time)
        
        return {
            'is_limited': False,
            'reset_time': current_time + window_size,
            'remaining_requests': max_requests - len(requests),
            'retry_after': 0
        }
    
    def get_client_identifier(self) -> str:
        """Get a unique identifier for the client"""
        # Use IP address as identifier
        # In production, you might want to use user ID or session ID
        return request.environ.get('REMOTE_ADDR', '127.0.0.1')
    
    def rate_limit_decorator(self, service: str = 'general'):
        """Decorator to apply rate limiting to Flask routes"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                identifier = self.get_client_identifier()
                rate_limit_result = self.is_rate_limited(identifier, service)
                
                if rate_limit_result['is_limited']:
                    logger.warning(f"Rate limit exceeded for {identifier} on service {service}")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'service': service,
                        'retry_after': rate_limit_result['retry_after'],
                        'reset_time': rate_limit_result['reset_time']
                    }), 429
                
                # Store rate limit info in Flask's g object for use in response headers
                g.rate_limit_remaining = rate_limit_result['remaining_requests']
                g.rate_limit_reset = rate_limit_result['reset_time']
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

# Global rate limiter instance
rate_limiter = RateLimiter()

# Convenience decorators for different services
def rate_limit_assemblyai(f):
    return rate_limiter.rate_limit_decorator('assemblyai')(f)

def rate_limit_google_tts(f):
    return rate_limiter.rate_limit_decorator('google_tts')(f)

def rate_limit_cohere(f):
    return rate_limiter.rate_limit_decorator('cohere')(f)

def rate_limit_together_ai(f):
    return rate_limiter.rate_limit_decorator('together_ai')(f)

def rate_limit_general(f):
    return rate_limiter.rate_limit_decorator('general')(f)

class CircuitBreaker:
    """Circuit breaker pattern for handling API failures"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = defaultdict(int)
        self.last_failure_time = defaultdict(float)
        self.state = defaultdict(str)  # 'closed', 'open', 'half-open'
    
    def call(self, service: str, func, *args, **kwargs):
        """Call a function with circuit breaker protection"""
        current_time = time.time()
        
        # Check if circuit is open
        if self.state[service] == 'open':
            if current_time - self.last_failure_time[service] > self.timeout:
                self.state[service] = 'half-open'
                logger.info(f"Circuit breaker for {service} moving to half-open state")
            else:
                raise Exception(f"Circuit breaker is open for {service}")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset failure count if we were in half-open state
            if self.state[service] == 'half-open':
                self.failure_count[service] = 0
                self.state[service] = 'closed'
                logger.info(f"Circuit breaker for {service} closed - service recovered")
            
            return result
            
        except Exception as e:
            self.failure_count[service] += 1
            self.last_failure_time[service] = current_time
            
            if self.failure_count[service] >= self.failure_threshold:
                self.state[service] = 'open'
                logger.error(f"Circuit breaker opened for {service} after {self.failure_count[service]} failures")
            
            raise e

# Global circuit breaker instance
circuit_breaker = CircuitBreaker()
