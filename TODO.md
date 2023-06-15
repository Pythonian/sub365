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
View subscriber detail and transaction history
Validate max_length in plan description (dj-mastery)
django messages/alert toast
enable serverowners to choose the interval: monthly, 3-months or 12-months
earnings are being calculated incorrectly for deleted users
Paginate Plan subscribers list
