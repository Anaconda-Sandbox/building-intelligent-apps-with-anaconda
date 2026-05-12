# Mission Critical
- [ ] conda-forge release: create a pinned version where everything is conda-forge, then push a release that is all anaconda channels. 
    - [ ] update all of the environment.yml so there's only defaults, main-x, and conda-pypi
- [ ] MAIN README: Update README to reflect all the changes and have a chart for how long it took you to get there.
- [ ] reference library: Remove all of the reference library and add it to a different branch
- [ ] example applications: Remove all of the example applications
- [ ] run everything in GH codespaces -- add to documentation that everything has been optimized for github codespaces when it does not require a desktop app: section #00-mcp-your-environment, only option Claude Desktop; section 02 - your first agent, option B: Anaconda Desktop; section 03 deployment and inference option A: Anaconda Desktop; section 08 native applications, option B: BeeWare builds native applications
- [ ] update example.environment.yml
- [ ] add `See a problem? Submit an Issue.` section to README
- [ ] Add `opininions` section to README - MetaFlow, conda-first ecosystem, trust security first package sources, see conda-forge pin for conda-forge version of this repo.
- [ ] Move code to Anaconda Labs
- [ ] Checks for every section
    - [ ] Runs in under 7 mintues
    - [ ] 
- [ ] 05, 06, 07, 08, 09: Complete the tutorials and make sure they run
    - [ ] 05: Label as experimental and requires Brev account -- see if we can get Brev codes
    - [ ] 06: Almost done, run 06 all the way through to make sure it works. 
    - [ ] 06: Make sure the agent harness is an appropriate approach to pulling the concepts together.
    - [ ] 07: upgrade from conda-lock to conda-lockfiles
    - [ ] 07: Fix so it doesn't have all those useless print statements
    - [ ] 07: Completion screen at the end of the nb
    - [ ] 08: Remove useless prints in markdown in natvie apps notebook. Do I even need a notebook? I think I can delete the entire notebook and just do a build script -- one for PyScript and one for BeeWare. 
        - [ ]: PyScript: if the PyScript app is already done, its just creating the environment and then running in the browser from a local server.
        - [ ]: BeeWare: What's the fastest point to getting the existing application running on your machine.
    - [ ] 09: Why pip? Can't I conda install panel?

# Nice to have
- [ ] screenshots: Add workflow on getting started for Anaconda Desktop
- [ ] screenshots and docs: add workflow for Agent Studio
- [ ] Anaconda CLI: add -- I think it should be rquired for 07 - mission critical infra
- [ ] Anaconda MCP: What is happening with MCP -- its not intutitive what to do here and requires claude code. 
- [ ] Anaconda Agent Studio: Add to 02-your-first agent - the goal would be to add a section where they use agent studio to create a new agent and then compare their output to what is in this repo.

# QTNA
- Do we want to have the `.conda` directory?
