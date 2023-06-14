- Introduce translations
- Unit tests where necessary
- Notifications for Serverowners and subscribers when an action is performed
    - New subscriber
    - Cancelled subscription
    - Reminder of next due subscription date
- Bug: Two owners of servers can still register a server
- Use HTMX to dynamically check for used subdomain name
- Admin interface overhaul
- Rewrite some URL patterns
- Check if earnings count stays if after someone subscribes, you delete plans
- Site responsiveness
- Error pages
- Setup for production environment
- Github worflow
- Makefile
- Reduce API calls by saving to database
Edit plan
View plan and all accounts who subscribed to it
Extract plan list into template
View subscriber detail and transaction history
Add max_length to plan description
Change how the empty state of the Plans template works
django messages/alert toast