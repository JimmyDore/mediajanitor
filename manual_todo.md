PRD

Manual
- Updated 3 days ago ? => Should be updated daily with celery task, there's a bug here
- change secret key in production
- DB backup

Marketing
- Add test pipeline for pull requests
- Make sure I'm open to pull requests but no one else than me can merge (see below)
- Readme.md (what the project does, how to use it, how to run it locally, how to deploy it, how to contribute)
- check what an open source project should have
- Shutdown sign ups for now => Put a waiting list page and send slack notification in new users instead
- Reddit post on jellyfin 

Process
- Test Ralph script


⏺ Committed. Here are the next steps:                                       
                                                                            
  Next Steps (Manual)                                                       
                                                                            
  1. Push to GitHub                                                         
                                                                            
  git push                                                                  
                                                                            
  2. Configure Branch Protection                                            
                                                                            
  After the workflow exists on main, go to your GitHub repo:                
                                                                            
  1. Settings → Branches → Add branch protection rule                       
  2. Branch name pattern: main                                              
  3. Enable: "Require status checks to pass before merging"                 
  4. Search and select required checks: backend, frontend                   
  5. Save changes                                                           
                                                                            
  3. Verify It Works                                                        
                                                                            
  1. Create a test branch with a small change                               
  2. Open a PR to main                                                      
  3. Watch the CI run - both jobs should appear                             
  4. Verify merge is blocked until checks pass                              
                                                                            
❯ what do I need to check ? I want to be able to merge to main, but I       
  don't want any individual contributors to open merge requests             
  ⎿  [Image #1]                                                             
                                                                            
⏺ For your use case, check only:                                            
                                                                            
  ✅ Require status checks to pass before merging                           
  - After checking this, click "Search for status checks" and add: backend  
  and frontend                                                              
                                                                            
  That's it. Leave everything else unchecked.                               
                                                                            
  ---                                                                       
  Why this works for you:                                                   
  - PRs will run CI and must pass before merge                              
  - As admin, you can still push directly to main (no PR required)          
  - You can bypass if needed since "Do not allow bypassing" is unchecked    
                                                                            
  About preventing others from opening PRs:                                 
  That's controlled in Settings → Collaborators, not branch protection. If  
  you haven't added any collaborators, no one else can push branches or open
   PRs on your repo anyway. If the repo is public, people can fork and open 
  PRs, but they can't merge without your approval.                          
                                                                            
❯ ok, I'd like people to be able to open PR. This will be an open           
  source project                                                            
                                                                            
⏺ For an open source project where anyone can open PRs but tests must pass: 
                                                                            
  Check these:                                                              
                                                                            
  1. ✅ Require a pull request before merging                               
    - This forces all changes (including yours) to go through PRs           
    - You'll see sub-options - you can leave "Require approvals" unchecked  
  if you don't need review from others                                      
  2. ✅ Require status checks to pass before merging                        
    - Add backend and frontend as required checks                           
    - Check "Require branches to be up to date before merging" (optional but
   recommended)                                                             
                                                                            
  Leave unchecked:                                                          
  - ❌ Do not allow bypassing - so you as admin can merge even if           
  something's stuck                                                         
                                                                            
  ---                                                                       
  Result:                                                                   
  - Anyone can fork and open a PR                                           
  - CI runs automatically on all PRs                                        
  - PRs can only merge if backend and frontend checks pass                  
  - You (admin) can merge or bypass if needed                               
                                                                            
❯ Ok my workflow is : I'm the boss, I can push on main whenever I want.     
  Other people can contribute and open PRs, Issues BUT the PRs should       
  be validated by me.                                                       
                                                                            
⏺ For that workflow, check these:                                           
                                                                            
  1. ✅ Require a pull request before merging                               
    - ✅ Require approvals → set to 1                                       
    - This means contributor PRs need your approval                         
  2. ✅ Require status checks to pass before merging                        
    - Add backend and frontend                                              
  3. ❌ Do not allow bypassing → leave UNCHECKED                            
    - This lets you (admin) push directly to main, bypassing the PR         
  requirement                                                               
                                                                            
  ---                                                                       
  Result:                                                                   
  - You can push directly to main anytime                                   
  - Contributors must open a PR                                             
  - Their PRs need CI to pass AND your approval                             
  - You click "Merge" when you're happy with their contribution   