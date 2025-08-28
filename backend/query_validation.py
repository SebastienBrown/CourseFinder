
from flask import Flask, request, jsonify
from functools import wraps
import time
from datetime import datetime

# =====================================================
# Simple, Focused Validation Class
# =====================================================

class QueryValidator:
    """Simple validation focused on actual risks for embeddings API."""
    
    def __init__(self):
        self.MAX_QUERY_LENGTH = 500     # API cost protection
        self.MIN_QUERY_LENGTH = 1       # Prevent empty queries
        
        # Simple rate limiting (in production, use Redis)
        self.request_counts = {}
        self.MAX_REQUESTS_PER_MINUTE = 10
    
    def validate(self, query: str) -> tuple[bool, str]:
        """Validate query and return (is_valid, error_message)."""
        
        # 1. Check if query exists and is string
        if not isinstance(query, str):
            return False, "Query must be a string"
        
        # 2. Check length (cost protection)
        if len(query.strip()) < self.MIN_QUERY_LENGTH:
            return False, "Query cannot be empty"
            
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long. Maximum {self.MAX_QUERY_LENGTH} characters"
        
        # 3. Check for null bytes (basic security)
        if '\x00' in query:
            return False, "Invalid characters in query"
        
        # Unicode is fine - OpenAI handles the complexity
        return True, "Valid query"
    
    def check_rate_limit(self, client_ip: str) -> tuple[bool, str]:
        """Simple rate limiting check."""
        current_time = time.time()
        
        # Initialize or clean old requests
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Remove requests older than 1 minute
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check if under limit
        if len(self.request_counts[client_ip]) >= self.MAX_REQUESTS_PER_MINUTE:
            return False, f"Rate limit exceeded. Max {self.MAX_REQUESTS_PER_MINUTE} requests per minute"
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        return True, "Within rate limits"

# Create global validator instance
validator = QueryValidator()