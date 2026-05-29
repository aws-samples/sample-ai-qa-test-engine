# VPC Deployment Requirements

## When to Use VPC Mode

Deploy in VPC mode when the test runner needs to access:
- Internal web applications (not publicly accessible)
- Databases (RDS, DynamoDB VPC endpoints, etc.)
- Private APIs behind internal load balancers

## Prerequisites

### 1. VPC with NAT Gateway

The test runner needs outbound internet access for AWS APIs (Bedrock, S3, ECR, Secrets Manager, AgentCore). This requires:

- **Private subnets** (at least 2, in different AZs)
- **NAT Gateway** in a public subnet with a route from the private subnets
- **VPC DNS** enabled (enableDnsHostnames + enableDnsSupport)

### 2. Security Group

Create a security group in the same VPC with these rules:

**Inbound Rules:**

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| None required | — | — | Runner initiates all connections outbound |

**Outbound Rules (minimum):**

| Type | Port | Destination | Purpose |
|------|------|-------------|---------|
| HTTPS | 443 | 0.0.0.0/0 | AWS APIs via NAT (Bedrock, S3, ECR, CloudWatch, Secrets Manager, AgentCore) |

**Outbound Rules (add per your environment):**

| Type | Port | Destination | Purpose |
|------|------|-------------|---------|
| HTTPS/HTTP | 443/80/custom | Internal app SG or CIDR | Access to application under test |
| PostgreSQL | 5432 | DB security group | Direct database verification |
| MySQL | 3306 | DB security group | Direct database verification |
| Custom | any | specific CIDR | Any other internal service |

**Your internal app's security group** also needs an inbound rule:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| HTTPS/HTTP | app port | Test runner SG | Allow runner to reach the app |

### 3. Subnet Requirements

| Requirement | Details |
|---|---|
| Type | Private (no IGW route) |
| Count | At least 2 (different AZs for HA) |
| NAT | Route to NAT Gateway for outbound internet |
| IP capacity | Each runner session uses 1 ENI = 1 private IP |

**Capacity planning**: If running 20 parallel scenarios, you need at least 20 available IPs across your subnets.

## Deploy Command

```bash
./scripts/deploy-infra.sh \
  --network-mode PRIVATE \
  --vpc-id vpc-0abc123def456 \
  --subnets subnet-aaa111,subnet-bbb222 \
  --security-groups sg-ccc333
```

Or pass a pre-created SG:
```bash
./scripts/deploy-infra.sh \
  --network-mode PRIVATE \
  --subnets subnet-aaa111,subnet-bbb222 \
  --security-groups sg-your-precreated-sg
```

## AgentCore Browser in VPC

The AgentCore Browser (`StartBrowserSession`) is a **managed AWS service** that runs in AWS's infrastructure, not your VPC. It accesses websites via the public internet.

**If your app is only accessible from your VPC:**

| Option | How | Trade-off |
|---|---|---|
| **Private ALB + VPC Lattice** | Expose internal app via a private endpoint the browser can reach | Requires networking setup |
| **Local Playwright in runner** | Runner uses its own browser (in-VPC) instead of AgentCore Browser | Loses remote browser benefits, needs more memory |
| **Browser proxy** | Configure AgentCore Browser to route through a proxy in your VPC | Requires proxy infrastructure |

For most internal app testing, **the runner itself is in the VPC** and can reach the app directly. The AgentCore Browser is only needed for public-facing sites or when you need the managed browser's anti-bot capabilities.
