#!/usr/bin/env python3
"""Inspect Anthropic SDK structure"""

from anthropic import Anthropic
import inspect

c = Anthropic()

print("=== ANTHROPIC SDK 0.105.2 STRUCTURE ===\n")

print("1. Standard API (client.messages)")
print(f"   - Method: {inspect.signature(c.messages.create)}\n")

print("2. Beta API (client.beta)")
print(f"   - Available: {[m for m in dir(c.beta) if not m.startswith('_')]}\n")

print("3. Beta Messages (client.beta.messages)")
print(f"   - Method: {inspect.signature(c.beta.messages.create)}\n")

print("4. Beta Agents (client.beta.agents)")
print(f"   - Methods: {[m for m in dir(c.beta.agents) if not m.startswith('_') and m not in ['with_raw_response', 'with_streaming_response']]}\n")

print("5. Beta Agents Create Signature")
print(f"   - {inspect.signature(c.beta.agents.create)}\n")

# Try to get the docstring
print("6. Beta Agents Documentation")
print(f"   - {c.beta.agents.__doc__ or 'No docstring'}\n")

print("7. Beta Sessions (if available)")
if hasattr(c.beta, 'sessions'):
    print(f"   - Methods: {[m for m in dir(c.beta.sessions) if not m.startswith('_') and m not in ['with_raw_response', 'with_streaming_response']]}")
    if hasattr(c.beta.sessions, 'create'):
        print(f"   - Create: {inspect.signature(c.beta.sessions.create)}")
else:
    print("   - Not available")

print("\n=== CRITICAL FINDING ===")
print("The beta.agents API is for MANAGING agents (CRUD), NOT for EXECUTING them.")
print("Current bridge implementation uses standard .messages.create() which is correct for execution.")
print("DECISION: Keep using .messages.create() with structured system prompt.")
