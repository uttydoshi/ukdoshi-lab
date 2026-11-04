from pathlib import Path

from aws_cdk import Annotations, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

from stacks.stage import ZONE_NAME, Stage

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist" / "frontend" / "browser"

# Rewrites extension-less paths (Angular client-side routes) to index.html, behind a browser password
# prompt. The expected credentials (base64 of "user:password") live in a CloudFront key-value store, set by
# scripts/site-password.sh and never in code. Until they're set, everyone is refused.
PASSWORD_REWRITE_JS = """
import cf from 'cloudfront';

const store = cf.kvs('KVS_ID');

async function handler(event) {
  var request = event.request;
  var expected = null;
  try {
    expected = await store.get('basic-auth');
  } catch (e) {}
  var given = request.headers.authorization ? request.headers.authorization.value : '';
  if (!expected || given !== 'Basic ' + expected) {
    return {
      statusCode: 401,
      statusDescription: 'Unauthorized',
      headers: { 'www-authenticate': { value: 'Basic realm="REALM", charset="UTF-8"' } },
    };
  }
  if (!request.uri.includes('.')) {
    request.uri = '/index.html';
  }
  return request;
}
"""

SPA_REWRITE_JS = """
function handler(event) {
  var request = event.request;
  if (!request.uri.includes('.')) {
    request.uri = '/index.html';
  }
  return request;
}
"""


class SiteStack(Stack):
    """Angular on S3 + CloudFront, on a subdomain of the main site's zone."""

    def __init__(self, scope: Construct, construct_id: str, *, stage: Stage, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        zone = route53.HostedZone.from_lookup(self, "Zone", domain_name=ZONE_NAME)

        # --- Frontend: private S3 bucket, only CloudFront can read it ---
        bucket = s3.Bucket(
            self,
            "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=stage.site_domain,
            validation=acm.CertificateValidation.from_dns(zone),
        )

        if stage.password:
            password_store = cloudfront.KeyValueStore(self, "PasswordStore")
            spa_rewrite = cloudfront.Function(
                self,
                "SpaRewrite",
                runtime=cloudfront.FunctionRuntime.JS_2_0,
                code=cloudfront.FunctionCode.from_inline(
                    PASSWORD_REWRITE_JS.replace("KVS_ID", password_store.key_value_store_id).replace(
                        "REALM", stage.site_domain
                    )
                ),
                key_value_store=password_store,
            )
            CfnOutput(self, "PasswordStoreArn", value=password_store.key_value_store_arn)
        else:
            spa_rewrite = cloudfront.Function(
                self,
                "SpaRewrite",
                runtime=cloudfront.FunctionRuntime.JS_2_0,
                code=cloudfront.FunctionCode.from_inline(SPA_REWRITE_JS),
            )

        # Every response carries the standard browser security headers. While it's being built, the lab
        # also asks search engines not to list it (it's password-protected, but its address isn't secret).
        headers = cloudfront.ResponseHeadersPolicy(
            self,
            "SecurityHeaders",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(365), include_subdomains=True, override=True
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(override=True),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY, override=True
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True,
                ),
            ),
            custom_headers_behavior=None
            if stage.search_engines
            else cloudfront.ResponseCustomHeadersBehavior(
                custom_headers=[
                    cloudfront.ResponseCustomHeader(header="X-Robots-Tag", value="noindex", override=True),
                ]
            ),
        )

        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            domain_names=[stage.site_domain],
            certificate=certificate,
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                response_headers_policy=headers,
                function_associations=[
                    cloudfront.FunctionAssociation(
                        function=spa_rewrite,
                        event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                    )
                ],
            ),
        )

        if FRONTEND_DIST.exists():
            s3deploy.BucketDeployment(
                self,
                "DeployFrontend",
                sources=[s3deploy.Source.asset(str(FRONTEND_DIST))],
                destination_bucket=bucket,
                distribution=distribution,
                distribution_paths=["/*"],
            )
        else:
            Annotations.of(self).add_warning(
                f"{FRONTEND_DIST} not found; run `npm run build` in frontend/ before deploying the site."
            )

        # --- DNS: the lab's name aliases to CloudFront (IPv4 + IPv6) ---
        cf_target = route53.RecordTarget.from_alias(targets.CloudFrontTarget(distribution))
        route53.ARecord(self, "SiteA", zone=zone, record_name=stage.site_domain, target=cf_target)
        route53.AaaaRecord(self, "SiteAaaa", zone=zone, record_name=stage.site_domain, target=cf_target)

        CfnOutput(self, "SiteUrl", value=f"https://{stage.site_domain}")
        CfnOutput(self, "CloudFrontUrl", value=f"https://{distribution.distribution_domain_name}")
