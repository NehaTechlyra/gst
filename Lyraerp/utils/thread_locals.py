"""
Thread-local storage for request-scoped data.

This module provides thread-safe storage for data that needs to be accessed
across different parts of the application during a single request, such as
the current company database and company code for URL generation.
"""

import threading

_thread_locals = threading.local()

# ============================================================================
# DATABASE THREAD LOCALS
# ============================================================================

def set_current_db(db_name):
    """Set the current company database for this thread/request"""
    _thread_locals.company_db = db_name

def get_current_db():
    """Get the current company database for this thread/request"""
    return getattr(_thread_locals, 'company_db', 'default')

def clear_current_db():
    """Clear the current company database (cleanup)"""
    if hasattr(_thread_locals, 'company_db'):
        del _thread_locals.company_db


# ============================================================================
# COMPANY CODE THREAD LOCALS (for URL reversing)
# ============================================================================

def set_current_company_code(company_code):
    """
    Set the current company code for this thread/request.
    Used by reverse() to automatically include company_code in URLs.
    """
    _thread_locals.company_code = company_code

def get_current_company_code():
    """
    Get the current company code for this thread/request.
    Returns None if no company code is set.
    """
    return getattr(_thread_locals, 'company_code', None)

def clear_current_company_code():
    """Clear the current company code (cleanup)"""
    if hasattr(_thread_locals, 'company_code'):
        del _thread_locals.company_code


# ============================================================================
# REQUEST THREAD LOCALS (for accessing request object globally)
# ============================================================================

def set_current_request(request):
    """Store the current request for access in reverse() and other utilities"""
    _thread_locals.request = request

def get_current_request():
    """Get the current request. Returns None if no request is set."""
    return getattr(_thread_locals, 'request', None)

def clear_current_request():
    """Clear the current request (cleanup)"""
    if hasattr(_thread_locals, 'request'):
        del _thread_locals.request


# ============================================================================
# CLEANUP UTILITY
# ============================================================================

def clear_all_thread_locals():
    """Clear all thread-local data. Called at the end of each request."""
    clear_current_db()
    clear_current_company_code()
    clear_current_request()