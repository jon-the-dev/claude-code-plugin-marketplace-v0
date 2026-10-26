---
tags: [security-headers]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We have an internal customer portal at https://portal.helixlogistics.net (Django on ECS Fargate behind an ALB, no CloudFront, DNS straight to the ALB via Route53). Security team's quarterly scan says we're a C on securityheaders.com and they want A+ by end of quarter. Platform team owns the ALB (terraform in alb.tf, attached) and would prefer the app team not touch nginx/gunicorn config. Current headers are in headers.txt. What exactly can be done on the ALB alone, what can't, and what's the minimal change on the app side if any? Write it up in plan.md with the terraform changes.
Input files: headers.txt, alb.tf
