---
tags: [security-headers]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

securityheaders.com gave our marketing site (https://www.acmeroadworks.com) a D and my boss wants it fixed this week. The site is a static Next.js export in S3 behind CloudFront, deployed from the terraform in this repo. I saved the current response headers in headers.txt and the CloudFront terraform is in cloudfront.tf. Figure out what is missing, update the terraform so we get an A+, and tell me anything that could break. We do use Google Analytics and Google Fonts on the site. Write the report to report.md.
Input files: headers.txt, cloudfront.tf
