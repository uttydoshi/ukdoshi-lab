#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.github_deploy_stack import GithubDeployStack
from stacks.site_stack import SiteStack
from stacks.stage import LIVE, STAGING

app = cdk.App()

# Everything lives in us-east-1: CloudFront only accepts ACM certificates from there.
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1")

# Two copies of the lab: live (lab.ukdoshi.com) and staging (staging.lab.ukdoshi.com).
# Both add records to the main site's ukdoshi.com zone (its UkdoshiDns stack), which must already exist.
for stage in (LIVE, STAGING):
    SiteStack(app, stage.stack_name("Site"), stage=stage, env=env)

# Deployed by hand, once: lets GitHub Actions deploy the stacks above on pushes to main (live) and staging.
# GitHub's token names the repo as owner@id/repo@id, so a renamed or recreated repo can't deploy.
GithubDeployStack(
    app,
    "UkdoshiLabGithubDeploy",
    repo="uttydoshi@83499703/ukdoshi-lab@1445651473",
    branches=["main", "staging"],
    env=env,
)

app.synth()
