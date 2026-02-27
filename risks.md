# Risk Analysis - Cloud Worker Orchestrator

## Executive Summary

This document outlines the identified risks, pain points, and failure modes for the Cloud Worker Orchestrator system. It serves as a reference for mitigation planning and operational awareness.

---

## 1. Pain Points (Most Likely Issues)

### 1.1 e2-micro RAM Insufficiency (CRITICAL)
- **Issue**: 0.6GB RAM cannot handle opencode + juggle + git + npm + Python simultaneously
- **Likelihood**: Near-certain under any real workload
- **Impact**: OOM kills, work failures, potential data loss
- **Mitigation**: 
  - Add 1-2GB swap file (will cause thrashing)
  - Use e2-small (~$6/mo) if budget allows
  - Run tools sequentially, not concurrently

### 1.2 Alpine Linux Compatibility (HIGH)
- **Issue**: 
  - opencode/juggle may have Python dependencies expecting glibc (Alpine uses musl)
  - Many Python wheels are compiled for glibc
  - npm packages may fail to install
- **Likelihood**: High
- **Impact**: Tool installation failures, VM unusable
- **Mitigation**:
  - Test in container first before provisioning
  - Fall back to Ubuntu minimal if needed
  - Consider using Python virtual environments

### 1.3 Terraform State Corruption (MEDIUM)
- **Issue**: Local state file can become corrupted or out of sync
- **Scenarios**:
  - VM created but terraform loses track → orphan billing
  - Terraform tries to recreate existing VM → conflicts
  - Concurrent runs corrupting state
- **Likelihood**: Medium over time
- **Impact**: Billing issues, deployment failures
- **Mitigation**:
  - Use state locking (even local)
  - Regular state backup
  - Manual state inspection after failures

### 1.4 SSH Race Conditions (MEDIUM)
- **Issue**: Ansible runs immediately after terraform but VM not ready
- **Likelihood**: Medium
- **Impact**: Provisioning failures, retries
- **Mitigation**:
  - Robust retry logic with exponential backoff
  - Health check script before Ansible runs

---

## 2. Failure Modes

| Failure Mode | Cause | Impact | Likelihood |
|--------------|-------|--------|------------|
| **OOM kill** | 0.6GB RAM insufficient | Work fails, data loss | HIGH |
| **Tool installation fails** | Alpine musl incompatibilities | VM unusable | HIGH |
| **Stuck VM** | Script crashes mid-execution | Ongoing billing | MEDIUM |
| **Git conflicts** | Concurrent modifications | Work loss | MEDIUM |
| **gh auth fails** | Token expired/revoked | Cannot push work | LOW |
| **Network timeout** | Poor connectivity | Work stalled | LOW |

---

## 3. Security Risks

### 3.1 GitHub Token Exposure (CRITICAL)

**Current Risk (in spec)**:
```hcl
metadata_startup_script = "... echo $GH_TOKEN | gh auth ..."
```

**Problem**: Token visible in:
- GCP metadata (anyone with compute.instances.get)
- Instance startup logs
- Process list (`ps aux` shows environment)
- Cloud logging

**Mitigation (REQUIRED)**:
```hcl
# Use GCP Secret Manager instead
resource "google_compute_instance" "worker" {
  metadata = {
    enable-oslogin = "TRUE"
  }
}
# Then fetch secret at runtime via Ansible
```

### 3.2 SSH Key Exposure (HIGH)

**Risk**: If private key leaked, attacker gains VM access

**Mitigation**:
- Store SSH key in GCP Secret Manager
- Use separate key per VM
- Rotate keys regularly
- Never commit keys to git

### 3.3 Firewall Misconfiguration (HIGH)

**Risk**: Port 22 exposed to internet instead of controller IP only

**Mitigation**:
```hcl
resource "google_compute_firewall" "ssh" {
  source_ranges = ["${var.controller_ip}/32"]
  allowed = [{ IPProtocol = "tcp", ports = ["22"] }]
}
```

### 3.4 Over-Privileged Service Account (HIGH)

**Risk**: Default compute service account has broad permissions

**Mitigation**:
```hcl
service_account {
  email  = google_service_account.worker.email
  scopes = ["https://www.googleapis.com/auth/cloud-platform"]  # Narrow!
}
```

### 3.5 No Audit Logging (MEDIUM)

**Risk**: No record of actions taken on VM

**Mitigation**:
- Enable Cloud Audit Logs
- Log all SSH commands
- Use VPC Flow Logs

---

## 4. Financial Risks

### 4.1 Orphaned VM (BIGGEST RISK)

**Scenario**: Script crashes mid-execution, no cleanup

| VM Type | Daily Cost | Monthly (if forgotten) |
|---------|------------|----------------------|
| e2-micro | ~$0.04 | ~$1.32/mo |
| e2-small | ~$0.20 | ~$6/mo |
| **Worst case** | - | **$100+/mo** |

**Mitigation (REQUIRED)**:
1. **Budget alerts**: Set GCP budget at $5 threshold
2. **Auto-shutdown**: Cron job to destroy VM after N hours of inactivity
3. **Health check**: Separate process monitoring VM state
4. **Tag all resources**: Enable cost breakdown by tag

### 4.2 Disk Charges (LOW-MEDIUM)

- 30GB standard disk = ~$1.20/mo
- Additional disks multiply cost
- Snapshot storage adds up

**Mitigation**:
- Use smallest disk possible
- Delete snapshots regularly
- Monitor disk usage

### 4.3 Network Egress (LOW)

- Free tier: 1GB/month
- Additional: ~$0.12/GB
- Large repos or many pushes = excess

**Mitigation**:
- Use shallow git clones
- Compress artifacts
- Monitor egress in GCP console

### 4.4 Accidental Larger VM (MEDIUM)

**Scenario**: User upgrades to e2-small "temporarily" and forgets

**Mitigation**:
- Hard-code machine type in Terraform
- Add comments explaining cost
- Use GCP organization policies to restrict instance creation

---

## 5. Cost Reality Check

| Scenario | Theoretical | Realistic | Worst Case |
|----------|-------------|-----------|-------------|
| e2-micro only | $0/mo | ~$1.32/mo | ~$1.32/mo |
| e2-small | $6/mo | $6/mo | $6/mo |
| Forgotten VM | $0 | $1.32-6/mo | $100+/mo |
| + Self-hosted AWX | $0 | +$5-10/mo | +$10/mo |
| **Total** | **$0** | **~$1.32-20/mo** | **$150+/mo** |

---

## 6. Recommended Mitigations (Priority Order)

### MUST DO (Before First Run)
1. Set GCP budget alert at $5
2. Use GCP Secret Manager for tokens
3. Add firewall rule restricting SSH to controller IP
4. Create minimal service account

### SHOULD DO (Before Production)
1. Test Alpine + opencode/juggle in container
2. Add auto-shutdown cron job
3. Add health check monitoring
4. Enable Cloud Audit Logs

### NICE TO HAVE (Future)
1. Use e2-small instead of e2-micro
2. Add Terraform state locking
3. Implement cost breakdown by tag
4. Add VPC Flow Logs

---

## 7. Decision Matrix

| Risk | Severity | Likelihood | Mitigation Effort |
|------|----------|------------|-------------------|
| Orphaned VM | HIGH | MEDIUM | LOW |
| Token Exposure | CRITICAL | HIGH | LOW |
| RAM Insufficient | HIGH | HIGH | LOW |
| Alpine Incompatibility | HIGH | HIGH | MEDIUM |
| Firewall Misconfig | HIGH | LOW | LOW |
| State Corruption | MEDIUM | MEDIUM | LOW |
| SSH Key Leak | HIGH | LOW | LOW |

---

**Bottom Line**: The biggest financial risk is orphaned VMs. The biggest security risk is token exposure. The biggest operational risk is RAM insufficiency.
