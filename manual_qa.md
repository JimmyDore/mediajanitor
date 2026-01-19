Prd
- if no pseudo available, then it shoud use default username
- Disappeared requests whitelisting => should be reinrtoduced
- No whitelisting for large series/movies ? => should be added
- Disappeared beautiful system/dark/white in settings & ugly select box for language
- Language issues not detected correctly for series episodes

Manual
- SMTP
- Test slack notif
- Updated 3 days ago ? => Should be updated daily with celery task, there's a bug here
- Change sonarr, radarr etc... logos
- DB backup 
- Split exploratory qa skill in multiple skills
- Test Email forgot password flow



Manual QA : 
QA Guide for Epic 21: Slack Notification Monitoring                                       
                                                                                            
  Prerequisites                                                                             
                                                                                            
  1. Create Slack webhooks at https://api.slack.com/apps → Create App → Incoming Webhooks   
  2. Set environment variables in your .env file or Docker:                                 
  SLACK_WEBHOOK_NEW_USERS=https://hooks.slack.com/services/xxx/yyy/zzz                      
  SLACK_WEBHOOK_SYNC_FAILURES=https://hooks.slack.com/services/xxx/yyy/zzz                  
                                                                                            
  Test 1: New User Signup Notification (US-21.2)                                            
                                                                                            
  # Start Docker                                                                            
  docker-compose up --build -d                                                              
                                                                                            
  # Register a new user                                                                     
  curl -X POST http://localhost:8080/api/auth/register \                                    
    -H "Content-Type: application/json" \                                                   
    -d '{"email":"test-slack@example.com","password":"TestPassword123!"}'                   
  Expected: Slack message with :wave: New User Signup, email, timestamp, total user count   
                                                                                            
  Test 2: Sync Failure Notification (US-21.3)                                               
                                                                                            
  # Login as a user with INVALID Jellyfin settings                                          
  TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \                            
    -H "Content-Type: application/json" \                                                   
    -d '{"email":"test-slack@example.com","password":"TestPassword123!"}' \                 
    | jq -r '.access_token')                                                                
                                                                                            
  # First configure invalid settings                                                        
  curl -X POST http://localhost:8080/api/settings \                                         
    -H "Authorization: Bearer $TOKEN" \                                                     
    -H "Content-Type: application/json" \                                                   
    -d '{"jellyfin_server_url":"http://invalid-server:8096","jellyfin_api_key":"bad-key"}'  
                                                                                            
  # Trigger a sync (will fail)                                                              
  curl -X POST http://localhost:8080/api/sync/trigger \                                     
    -H "Authorization: Bearer $TOKEN"                                                       
  Expected: Slack message with :warning: Sync Failed, user email, service name, error       
  message                                                                                   
                                                                                            
  Test 3: No Webhook Configured (Graceful Skip)                                             
                                                                                            
  # Remove webhook env vars and restart                                                     
  unset SLACK_WEBHOOK_NEW_USERS                                                             
  docker-compose up --build -d                                                              
                                                                                            
  # Register should still work without error                                                
  curl -X POST http://localhost:8080/api/auth/register \                                    
    -H "Content-Type: application/json" \                                                   
    -d '{"email":"no-slack@example.com","password":"TestPassword123!"}'                     
  Expected: Registration succeeds, no Slack message sent, no errors in logs  