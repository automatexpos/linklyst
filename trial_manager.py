#!/usr/bin/env python3
"""
Trial Management Script for Linklyst
This script helps manage trial accounts and subscription statuses.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import supabase
except ImportError:
    print("Error: Could not import supabase from app.py")
    print("Make sure this script is run from the correct directory.")
    sys.exit(1)

def check_trial_statuses():
    """Check and display current trial statuses"""
    print("=== Linklyst Trial Status Report ===")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Get all users with trial information
        users = supabase.table("users").select("*").execute()
        
        active_trials = 0
        expired_trials = 0
        paid_subscriptions = 0
        inactive_accounts = 0
        
        print("User Status Summary:")
        print("-" * 80)
        print(f"{'Username':<20} {'Email':<30} {'Status':<15} {'Trial End':<20}")
        print("-" * 80)
        
        for user in users.data:
            username = user.get('username', 'N/A')[:19]
            email = user.get('email', 'N/A')[:29]
            is_trial = user.get('is_trial', False)
            is_active = user.get('is_active', False)
            subscription_status = user.get('subscription_status', 'unknown')
            trial_end = user.get('trial_end')
            
            if subscription_status == 'active':
                status = "PAID"
                trial_end_display = "N/A (Paid)"
                paid_subscriptions += 1
            elif is_trial and trial_end:
                trial_end_date = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
                now = datetime.now(trial_end_date.tzinfo)
                
                if now > trial_end_date:
                    status = "EXPIRED"
                    expired_trials += 1
                else:
                    days_left = (trial_end_date - now).days
                    status = f"TRIAL ({days_left}d)"
                    active_trials += 1
                
                trial_end_display = trial_end_date.strftime('%Y-%m-%d')
            elif not is_active:
                status = "INACTIVE"
                trial_end_display = "N/A"
                inactive_accounts += 1
            else:
                status = "UNKNOWN"
                trial_end_display = "N/A"
            
            print(f"{username:<20} {email:<30} {status:<15} {trial_end_display:<20}")
        
        print("-" * 80)
        print(f"\nSummary:")
        print(f"Active Trials: {active_trials}")
        print(f"Expired Trials: {expired_trials}")
        print(f"Paid Subscriptions: {paid_subscriptions}")
        print(f"Inactive Accounts: {inactive_accounts}")
        print(f"Total Users: {len(users.data)}")
        
    except Exception as e:
        print(f"Error fetching user data: {e}")

def expire_trials():
    """Manually expire trials that have passed their end date"""
    print("=== Expiring Overdue Trials ===")
    
    try:
        # Get users with active trials
        users = supabase.table("users").select("*").eq("is_trial", True).execute()
        
        expired_count = 0
        now = datetime.utcnow()
        
        for user in users.data:
            trial_end = user.get('trial_end')
            if not trial_end:
                continue
                
            trial_end_date = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
            
            if now.replace(tzinfo=trial_end_date.tzinfo) > trial_end_date:
                # Trial has expired
                result = supabase.table("users").update({
                    "is_active": False,
                    "is_trial": False,
                    "subscription_status": "expired"
                }).eq("id", user["id"]).execute()
                
                if result.data:
                    print(f"Expired trial for user: {user.get('username')} ({user.get('email')})")
                    expired_count += 1
        
        print(f"\nExpired {expired_count} overdue trials.")
        
    except Exception as e:
        print(f"Error expiring trials: {e}")

def extend_trial(username, days=7):
    """Extend a user's trial by specified number of days"""
    print(f"=== Extending Trial for {username} ===")
    
    try:
        # Find user
        user_result = supabase.table("users").select("*").eq("username", username).execute()
        
        if not user_result.data:
            print(f"User '{username}' not found.")
            return
            
        user = user_result.data[0]
        current_trial_end = user.get('trial_end')
        
        if current_trial_end:
            # Extend from current end date
            current_end = datetime.fromisoformat(current_trial_end.replace('Z', '+00:00'))
            new_end = current_end + timedelta(days=days)
        else:
            # Set new trial end date
            new_end = datetime.utcnow() + timedelta(days=days)
        
        # Update user
        result = supabase.table("users").update({
            "trial_end": new_end.isoformat(),
            "is_trial": True,
            "is_active": True,
            "subscription_status": "trial"
        }).eq("id", user["id"]).execute()
        
        if result.data:
            print(f"Successfully extended trial for {username} until {new_end.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"Failed to extend trial for {username}")
            
    except Exception as e:
        print(f"Error extending trial: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python trial_manager.py status           - Check trial statuses")
        print("  python trial_manager.py expire           - Expire overdue trials")
        print("  python trial_manager.py extend <username> [days] - Extend user trial")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        check_trial_statuses()
    elif command == "expire":
        expire_trials()
    elif command == "extend":
        if len(sys.argv) < 3:
            print("Error: Username required for extend command")
            sys.exit(1)
        username = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        extend_trial(username, days)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)