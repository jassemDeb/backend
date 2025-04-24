"""
Test script for rate limiting in the multilingual chat API.
This script sends multiple requests to different endpoints to test rate limiting.
"""
import requests
import time
import json
import argparse

def test_rate_limit(base_url, endpoint, token=None, requests_count=15, delay=0.1):
    """
    Test rate limiting on a specific endpoint
    
    Args:
        base_url: Base URL of the API
        endpoint: Endpoint to test
        token: Authentication token (if needed)
        requests_count: Number of requests to send
        delay: Delay between requests in seconds
    """
    url = f"{base_url}{endpoint}"
    headers = {}
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    print(f"\n\n{'='*50}")
    print(f"Testing rate limit for: {endpoint}")
    print(f"Making {requests_count} requests with {delay}s delay")
    print(f"{'='*50}\n")
    
    success_count = 0
    rate_limited_count = 0
    
    for i in range(requests_count):
        print(f"Request {i+1}/{requests_count}... ", end="", flush=True)
        
        try:
            if endpoint == '/api/auth/login/':
                # For login endpoint, we need to send credentials
                response = requests.post(
                    url, 
                    json={"email": "test@example.com", "password": "wrongpassword"},
                    headers=headers
                )
            elif endpoint == '/api/chat/ai/':
                # For AI chat endpoint
                response = requests.post(
                    url, 
                    json={"message": "Test message", "model": "lamini-t5"},
                    headers=headers
                )
            elif endpoint == '/api/chat/summary/':
                # For chat summary endpoint
                response = requests.post(
                    url, 
                    json={"language": "en"},
                    headers=headers
                )
            else:
                # For other endpoints
                response = requests.get(url, headers=headers)
            
            if response.status_code == 429:
                print("RATE LIMITED ❌")
                rate_limited_count += 1
                print(f"  Response: {response.json()}")
            elif response.status_code in (200, 201, 400, 401):
                print("SUCCESS ✓")
                success_count += 1
            else:
                print(f"OTHER ERROR ({response.status_code}) ⚠️")
                print(f"  Response: {response.text[:100]}...")
            
            time.sleep(delay)
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
    
    print(f"\nResults for {endpoint}:")
    print(f"  Success: {success_count}/{requests_count}")
    print(f"  Rate Limited: {rate_limited_count}/{requests_count}")
    print(f"  Rate Limit Percentage: {(rate_limited_count/requests_count)*100:.1f}%")
    
    return rate_limited_count > 0

def login(base_url, username, password):
    """Get authentication token"""
    url = f"{base_url}/api/auth/login/"
    response = requests.post(url, json={"email": username, "password": password})
    
    if response.status_code == 200:
        return response.json().get('access')
    else:
        print(f"Login failed: {response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test rate limiting on the API')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL of the API')
    parser.add_argument('--username', default='', help='Username for authentication')
    parser.add_argument('--password', default='', help='Password for authentication')
    parser.add_argument('--requests', type=int, default=15, help='Number of requests to send')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    # Endpoints to test
    endpoints = [
        # Auth endpoints (no auth required)
        '/api/auth/login/',
        
        # Endpoints requiring authentication
        '/api/chat/ai/',
        '/api/chat/summary/',
        '/api/profile/detail/',
        '/api/conversations/',
    ]
    
    token = None
    if args.username and args.password:
        print(f"Logging in as {args.username}...")
        token = login(args.base_url, args.username, args.password)
        if token:
            print("Login successful!")
        else:
            print("Login failed. Testing only unauthenticated endpoints.")
    
    results = {}
    
    # Test unauthenticated endpoints
    for endpoint in ['/api/auth/login/']:
        results[endpoint] = test_rate_limit(
            args.base_url, 
            endpoint, 
            token=None,
            requests_count=args.requests,
            delay=args.delay
        )
    
    # Test authenticated endpoints if we have a token
    if token:
        for endpoint in [e for e in endpoints if e != '/api/auth/login/']:
            results[endpoint] = test_rate_limit(
                args.base_url, 
                endpoint, 
                token=token,
                requests_count=args.requests,
                delay=args.delay
            )
    
    # Summary
    print("\n\n" + "="*50)
    print("RATE LIMIT TESTING SUMMARY")
    print("="*50)
    
    for endpoint, was_limited in results.items():
        status = "✓ WORKING" if was_limited else "❌ NOT WORKING"
        print(f"{endpoint}: {status}")

if __name__ == "__main__":
    main()
