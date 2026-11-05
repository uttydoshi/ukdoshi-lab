# Utty's lab

The source for **[lab.ukdoshi.com](https://lab.ukdoshi.com)**: small AI experiments, each one showing three
things: an LLM doing something useful or fun, a trace of every call it makes, and evals that measure the quality
of what it says. It runs serverless on AWS, with a pipeline that tests every change on a password-protected
staging copy before it goes live.

The first experiment is **The Couch Critics**: after each run, my two toy poodles, who stayed home on the couch,
review it in their own voices using the real run data. It's being built now, so the lab is password-protected
for the moment.

I designed and built it with [Claude Code](https://claude.com/claude-code), using the same stack and ways of
working as my main site, [ukdoshi.com](https://ukdoshi.com) ([source](https://github.com/uttydoshi/ukdoshi-site)).

## At a glance

| | |
|---|---|
| **Frontend** | Angular (TypeScript), served from S3 through CloudFront |
| **Infrastructure** | All of it defined in Python with the AWS CDK |
| **CI/CD** | GitHub Actions: tests, builds and deploys every push, logging in to AWS with OIDC (no stored keys) |
| **Environments** | `staging` branch → staging copy · `main` branch → lab.ukdoshi.com (both password-protected for now) |
| **Coming next** | A Python (FastAPI) backend on AWS Lambda, the Claude API, tracing of every call, and evals gated in CI |

## What's in the repo

| Folder | What's inside |
|---|---|
| [`frontend/`](frontend) | The Angular site: pages in `src/app/pages`, staging markers in `src/app/staging.ts` |
| [`infra/`](infra) | The AWS CDK app: a site stack for each of live and staging, and the role GitHub deploys with |
| [`scripts/`](scripts) | Owner tools: set the password each copy asks for |
| [`.github/workflows/`](.github/workflows) | The deploy pipeline |

No secrets live in this repo. The IDs you'll come across (like the AWS account) are public by design; the
passwords are stored in AWS, and so will the API keys be.

## Running it locally

You need Node.js 24.

```bash
# Frontend: http://localhost:4300 (4300, so it can run beside the main site on 4200)
cd frontend
npm install
npm test -- --watch=false                     # run the tests
npm start                                     # start the site
```

## How changes go live

Every push runs [`deploy.yml`](.github/workflows/deploy.yml): frontend tests, a production build, then a CDK
deploy. A failing test stops the deploy.

| Branch | Deploys to | Stacks |
|---|---|---|
| `staging` | the staging copy | `UkdoshiLabStagingSite` |
| `main` | [lab.ukdoshi.com](https://lab.ukdoshi.com) | `UkdoshiLabSite` |

The usual flow: make changes on `staging`, check them on the staging copy, then merge into `main`. The staging
copy is marked so it's never mistaken for live: a "Staging" badge, "[Staging]" in the tab title, an amber dot on
the tab icon, and the commit it was built from in the footer.

```bash
git switch staging && git merge main              # start from what's live
# ...make changes and commit...
git push                                          # updates the staging copy
git switch main && git merge staging && git push  # updates lab.ukdoshi.com
```

The **Actions** tab shows each run, and **Run workflow** there redeploys a branch by hand.

## For the owner: AWS setup and admin

These need AWS access to the site's account. I use an SSO profile called `ukdoshi`; the scripts default
to it, or set `AWS_PROFILE` to your own.

The lab shares an AWS account with the main site and builds on two of its stacks, which must be deployed
first: `UkdoshiDns` (the `ukdoshi.com` zone, where the lab adds its addresses) and `UkdoshiGithubDeploy` (the
account's GitHub sign-in provider, which the lab's deploy role reuses). The account is already prepared for the
CDK (`cdk bootstrap`).

**One-time setup**

```bash
# Log in to AWS
aws sso login --profile ukdoshi
export AWS_PROFILE=ukdoshi

# Install the CDK app's dependencies
cd infra
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Create the role GitHub Actions deploys with (by hand, once)
cdk deploy UkdoshiLabGithubDeploy
```

**Passwords.** `scripts/site-password.sh` sets the username and password lab.ukdoshi.com asks for;
`scripts/site-password.sh --staging` does the same for the staging copy. They're stored in AWS, never in this
repo.

---

© 2026 Utkarsh Doshi. This code is shared to read; all rights reserved.
