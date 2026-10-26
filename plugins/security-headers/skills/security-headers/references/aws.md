# AWS: where to set security headers

Pick the section for the layer that serves the public response (SKILL.md
step 3 explains how to tell). When two layers are stacked (CloudFront in
front of ALB, Cloudflare in front of CloudFront) set the static headers once,
at the outermost AWS layer you control, and remove any duplicate from the
inner layer.

## Contents

1. CloudFront: response headers policy (preferred for anything behind CloudFront)
2. CloudFront Functions / Lambda@Edge (dynamic cases)
3. Application Load Balancer: listener header modification
4. API Gateway
5. Amplify Hosting
6. S3 static website
7. Elastic Beanstalk, EC2, ECS (origin-level nginx/Apache)
8. Lambda function URLs, App Runner
9. Verification commands

---

## 1. CloudFront response headers policy

A response headers policy attaches to a **cache behavior** and is applied on
every response for that behavior, including cache hits, so it needs no
invalidation. It does need to be attached to *every* behavior that serves
HTML (default plus path-pattern behaviors), which is the usual reason a fix
"did not work".

### Managed policies (quick, incomplete)

| Name | ID | Sets |
|---|---|---|
| `SecurityHeadersPolicy` | `67f7725c-6f97-4210-82d7-5512b31e9d03` | HSTS (1 year), `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-XSS-Protection: 1; mode=block` |
| `CORS-and-SecurityHeadersPolicy` | `e61eb60c-9c35-4d20-a928-2b84e02af89c` | the above plus permissive CORS |

They lack CSP and Permissions-Policy and add the deprecated
`X-XSS-Protection`, so the best they reach is roughly a C with a warning.
Confirm current contents with
`aws cloudfront get-response-headers-policy --id <id>` before quoting them.
Use a custom policy for an A+.

### Custom policy: AWS CLI

`policy.json`:

```json
{
  "Name": "security-headers-aplus",
  "Comment": "A+ on securityheaders.com",
  "SecurityHeadersConfig": {
    "StrictTransportSecurity": {
      "Override": true,
      "IncludeSubdomains": true,
      "Preload": false,
      "AccessControlMaxAgeSec": 31536000
    },
    "ContentSecurityPolicy": {
      "Override": true,
      "ContentSecurityPolicy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests"
    },
    "FrameOptions": { "Override": true, "FrameOption": "DENY" },
    "ContentTypeOptions": { "Override": true },
    "ReferrerPolicy": { "Override": true, "ReferrerPolicy": "strict-origin-when-cross-origin" }
  },
  "CustomHeadersConfig": {
    "Quantity": 1,
    "Items": [
      {
        "Header": "Permissions-Policy",
        "Value": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
        "Override": true
      }
    ]
  },
  "RemoveHeadersConfig": {
    "Quantity": 2,
    "Items": [ { "Header": "Server" }, { "Header": "X-Powered-By" } ]
  }
}
```

```bash
aws cloudfront create-response-headers-policy --response-headers-policy-config file://policy.json
# then attach the returned Id to each cache behavior (console, or update-distribution with the full config)
aws cloudfront get-distribution-config --id DIST_ID > dist.json   # edit DefaultCacheBehavior.ResponseHeadersPolicyId and each CacheBehaviors[].ResponseHeadersPolicyId
```

`Override: true` means the policy wins when the origin sends the same header,
which is what you want so the origin cannot regress the grade. For a
Report-Only CSP rollout put `Content-Security-Policy-Report-Only` in
`CustomHeadersConfig` instead of `ContentSecurityPolicy`.

Headers CloudFront cannot remove with `RemoveHeadersConfig` include
`Via`, `X-Cache`, `X-Amz-Cf-*`, `Transfer-Encoding`, and a few connection
headers; `Server` and `X-Powered-By` can be removed.

### Terraform

```hcl
resource "aws_cloudfront_response_headers_policy" "security" {
  name    = "security-headers-aplus"
  comment = "A+ on securityheaders.com"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = false
      override                   = true
    }
    content_security_policy {
      content_security_policy = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests"
      override                = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    content_type_options {
      override = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }

  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
      override = true
    }
  }

  remove_headers_config {
    items { header = "Server" }
    items { header = "X-Powered-By" }
  }
}

resource "aws_cloudfront_distribution" "site" {
  # ...
  default_cache_behavior {
    # ...
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }
  # repeat response_headers_policy_id in every ordered_cache_behavior that serves HTML
}
```

### CloudFormation

```yaml
SecurityHeadersPolicy:
  Type: AWS::CloudFront::ResponseHeadersPolicy
  Properties:
    ResponseHeadersPolicyConfig:
      Name: security-headers-aplus
      SecurityHeadersConfig:
        StrictTransportSecurity:
          AccessControlMaxAgeSec: 31536000
          IncludeSubdomains: true
          Preload: false
          Override: true
        ContentSecurityPolicy:
          ContentSecurityPolicy: "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests"
          Override: true
        FrameOptions:
          FrameOption: DENY
          Override: true
        ContentTypeOptions:
          Override: true
        ReferrerPolicy:
          ReferrerPolicy: strict-origin-when-cross-origin
          Override: true
      CustomHeadersConfig:
        Items:
          - Header: Permissions-Policy
            Value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
            Override: true
      RemoveHeadersConfig:
        Items:
          - Header: Server
          - Header: X-Powered-By

# In the distribution:
#   DefaultCacheBehavior:
#     ResponseHeadersPolicyId: !Ref SecurityHeadersPolicy
```

### CDK (TypeScript)

```ts
const policy = new cloudfront.ResponseHeadersPolicy(this, "SecurityHeaders", {
  responseHeadersPolicyName: "security-headers-aplus",
  securityHeadersBehavior: {
    strictTransportSecurity: { accessControlMaxAge: Duration.days(365), includeSubdomains: true, preload: false, override: true },
    contentSecurityPolicy: { contentSecurityPolicy: "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests", override: true },
    frameOptions: { frameOption: cloudfront.HeadersFrameOption.DENY, override: true },
    contentTypeOptions: { override: true },
    referrerPolicy: { referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN, override: true },
  },
  customHeadersBehavior: {
    customHeaders: [{ header: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()", override: true }],
  },
  removeHeaders: ["Server", "X-Powered-By"],
});
// defaultBehavior: { origin, responseHeadersPolicy: policy, ... }
```

Deploy takes a few minutes to propagate. Re-scan after the distribution
status returns to `Deployed`.

## 2. CloudFront Functions / Lambda@Edge

Use only when the header value must vary per response (CSP nonces, per-path
policies that cannot be expressed as cache behaviors). A viewer-response
CloudFront Function:

```js
function handler(event) {
  var response = event.response;
  var h = response.headers;
  h['strict-transport-security'] = { value: 'max-age=31536000; includeSubDomains' };
  h['x-content-type-options']    = { value: 'nosniff' };
  h['x-frame-options']           = { value: 'DENY' };
  h['referrer-policy']           = { value: 'strict-origin-when-cross-origin' };
  h['permissions-policy']        = { value: 'camera=(), microphone=(), geolocation=()' };
  h['content-security-policy']   = { value: "default-src 'self'; frame-ancestors 'none'" };
  delete h['server'];
  delete h['x-powered-by'];
  return response;
}
```

Attach it as `viewer-response` on the behavior. A response headers policy
is cheaper and declarative; prefer it unless you need logic. For nonces you
need Lambda@Edge at `origin-response` with HTML rewriting, or generate the
nonce in the app and let CloudFront pass the origin's CSP through (set no
CSP in the policy, or `Override: false`).

## 3. Application Load Balancer

Since November 2024 an ALB listener can insert or overwrite a fixed set of
response headers. The ALB overwrites the header if the target sent one and
adds it otherwise. Supported security attributes:

| Listener attribute | Header |
|---|---|
| `routing.http.response.strict_transport_security.header_value` | `Strict-Transport-Security` |
| `routing.http.response.content_security_policy.header_value` | `Content-Security-Policy` |
| `routing.http.response.x_content_type_options.header_value` | `X-Content-Type-Options` |
| `routing.http.response.x_frame_options.header_value` | `X-Frame-Options` |
| `routing.http.response.server.enabled` (`false`) | suppresses the `Server: awselb/2.0` header the ALB adds when the target sent none |
| `routing.http.response.access_control_*` | CORS headers |

**Not supported:** `Referrer-Policy`, `Permissions-Policy`, removing
`X-Powered-By`. Those must come from the application (see headers.md
section 9) or a CloudFront distribution in front. State this limitation
when the ALB is the only edge; an ALB-only fix tops out around a B.

Set them on the **HTTPS (443) listener**; the HTTP listener should be a
301 redirect to HTTPS and needs nothing.

```bash
aws elbv2 modify-listener-attributes --listener-arn "$LISTENER_ARN" --attributes \
  Key=routing.http.response.strict_transport_security.header_value,Value="max-age=31536000; includeSubDomains" \
  Key=routing.http.response.x_content_type_options.header_value,Value=nosniff \
  Key=routing.http.response.x_frame_options.header_value,Value=DENY \
  Key=routing.http.response.content_security_policy.header_value,Value="default-src 'self'; frame-ancestors 'none'" \
  Key=routing.http.response.server.enabled,Value=false
aws elbv2 describe-listener-attributes --listener-arn "$LISTENER_ARN"
```

Terraform (`aws_lb_listener`, provider 5.78+):

```hcl
resource "aws_lb_listener" "https" {
  # ...
  routing_http_response_strict_transport_security_header_value = "max-age=31536000; includeSubDomains"
  routing_http_response_x_content_type_options_header_value    = "nosniff"
  routing_http_response_x_frame_options_header_value           = "DENY"
  routing_http_response_content_security_policy_header_value   = "default-src 'self'; frame-ancestors 'none'"
  routing_http_response_server_enabled                         = false
}
```

CloudFormation (`AWS::ElasticLoadBalancingV2::Listener`):

```yaml
ListenerAttributes:
  - Key: routing.http.response.strict_transport_security.header_value
    Value: "max-age=31536000; includeSubDomains"
  - Key: routing.http.response.x_content_type_options.header_value
    Value: nosniff
  - Key: routing.http.response.x_frame_options.header_value
    Value: DENY
  - Key: routing.http.response.server.enabled
    Value: "false"
```

The console does not always display these attributes; verify with `curl`.
EKS users with the AWS Load Balancer Controller: set them through the
`alb.ingress.kubernetes.io/listener-attributes.HTTPS-443` annotation.

## 4. API Gateway

- **REST API:** headers on normal responses come from the integration
  response (Lambda proxy: return them in `headers`; non-proxy: map them in
  the method response + integration response). For error paths set
  **Gateway Responses** (`DEFAULT_4XX`, `DEFAULT_5XX`) response parameters:
  `gatewayresponse.header.Strict-Transport-Security: "'max-age=31536000; includeSubDomains'"`
  (note the single quotes inside the double quotes).
- **HTTP API:** no header injection feature; return headers from the
  integration (Lambda) or put CloudFront in front with a response headers
  policy, which is also the right move when the API shares a domain with a
  site.
- An API that only serves JSON still benefits from HSTS, `nosniff`,
  `X-Frame-Options: DENY`, and a CSP of `default-src 'none'; frame-ancestors 'none'`.

## 5. Amplify Hosting

Commit `customHttp.yml` at the repo root (or monorepo root). File-based
headers override console-defined ones and take effect on the next deploy.

```yaml
customHeaders:
  - pattern: '**'
    headers:
      - key: Strict-Transport-Security
        value: 'max-age=31536000; includeSubDomains'
      - key: Content-Security-Policy
        value: "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests"
      - key: X-Frame-Options
        value: DENY
      - key: X-Content-Type-Options
        value: nosniff
      - key: Referrer-Policy
        value: strict-origin-when-cross-origin
      - key: Permissions-Policy
        value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()'
```

Trigger a redeploy afterwards. Patterns can scope a different CSP to
`/api/**` or `/embed/**` if one path must be framed.

## 6. S3 static website

S3 cannot add response headers. The fix is architectural: put CloudFront in
front (origin access control, bucket private), attach the response headers
policy from section 1, and point DNS at the distribution. This also gets
HTTPS on a custom domain, which the S3 website endpoint cannot do. Make sure
uploaded objects carry a correct `Content-Type`, because `nosniff` blocks
scripts and styles served as `binary/octet-stream`.

## 7. Elastic Beanstalk, EC2, ECS at the origin

Only needed when nothing sits in front, or for `Referrer-Policy` and
`Permissions-Policy` behind an ALB.

Elastic Beanstalk (Amazon Linux 2 / 2023, nginx): add
`.platform/nginx/conf.d/security_headers.conf`:

```nginx
server_tokens off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" always;
add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none'" always;
```

`always` makes nginx add them on error responses too. If a `location`
block elsewhere uses `add_header`, it replaces this list for that location
(nginx inheritance rule), so repeat or `include` the file there. Strip
`X-Powered-By` with `proxy_hide_header X-Powered-By;` when proxying to an
app server.

Apache: `Header always set <Name> "<value>"` in the vhost plus
`ServerTokens Prod` and `Header unset X-Powered-By`.

Container images on ECS behind an ALB: same nginx/Apache snippet in the
image, or the framework helper in headers.md section 9.

## 8. Lambda function URLs, App Runner

No edge header feature. Return the headers from the handler or framework
middleware (headers.md section 9), or front with CloudFront. App Runner
custom domains can sit behind CloudFront as a custom origin.

## 9. Verification

```bash
# public edge
curl -sS -D - -o /dev/null https://example.com/ | grep -iE '^(strict-transport|content-security|x-frame|x-content-type|referrer|permissions|server|x-powered-by|via|x-cache)'
# origin directly (bypass CloudFront) to confirm the edge is adding, not the origin
curl -sS -D - -o /dev/null -H 'Host: example.com' https://origin.example.com/
# CloudFront propagation
aws cloudfront get-distribution --id DIST_ID --query 'Distribution.Status'
# ALB
aws elbv2 describe-listener-attributes --listener-arn "$LISTENER_ARN"
```

Then re-run `scan_headers.py` and diff against the saved `before.json`.
