# Cloud Worker Orchestration System - Specification

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONTROL PLANE (Local/Existing)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │  GitHub API  │    │  Juggle API  │    │  Cloud APIs  │                 │
│  │  (webhooks)  │    │  (monitor)   │    │  (GCP REST)  │                 │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                 │
│         │                   │                   │                         │
│         └───────────────────┼───────────────────┘                         │
│                             ▼                                              │
│                  ┌──────────────────────┐                                 │
│                  │   Terraform + CLI   │                                 │
│                  │   Ansible Runner    │                                 │
│                  │                      │                                 │
│                  │  • VM Provisioning   │                                 │
│                  │  • Config Mgmt      │                                 │
│                  │  • State Management  │                                 │
│                  │  • Security Scans   │                                 │
│                  │  • Task/Ball Check  │                                 │
│                  │  • Auto-shutdown    │                                 │
│                  └──────────┬───────────┘                                 │
│                             │                                              │
│                             │ SSH + Cloud-Init                             │
│                             ▼                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           TARGET VM (GCP e2-micro)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌────────────────────────────────────────────────────────────────┐       │
│   │                    GUEST OS (Alpine Linux)                     │       │
│   ├────────────────────────────────────────────────────────────────┤       │
│   │                                                                │       │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │       │
│   │   │    Git      │  │    gh CLI   │  │   Python    │           │       │
│   │   │  (config)   │  │  (auth)     │  │   3.x       │           │       │
│   │   └─────────────┘  └─────────────┘  └─────────────┘           │       │
│   │                                                                │       │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │       │
│   │   │   OpenCode  │  │   Juggle    │  │   Scripts   │           │       │
│   │   │   (agent)   │  │   (TUI/CLI) │  │   (setup)   │           │       │
│   │   └─────────────┘  └─────────────┘  └─────────────┘           │       │
│   │                                                                │       │
│   │   ┌─────────────────────────────────────────────┐              │       │
│   │   │          Work Directory (/workspace)        │              │       │
│   │   │   • repo clone → agent work → git push      │              │       │
│   │   └─────────────────────────────────────────────┘              │       │
│   │                                                                │       │
│   └────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Overview

**Project Name:** Cloud Worker Orchestrator (CWO)
**Type:** Automated VM provisioning and management system
**Core Functionality:** Spin up ephemeral headless cloud VMs on GCP using Terraform, configure them with Ansible, provision development tools (git, gh, opencode, juggle), execute autonomous agent work, and auto-shutdown when idle.
**Target Users:** Developers using juggle/opencode agents for automated development

---

## 2. Infrastructure as Code Tools

> **IMPORTANT**: Before deploying, review [risks.md](./risks.md) for security and financial risk mitigations.

### 2.1 Terraform

**Purpose:** VM provisioning and lifecycle management

| Aspect | Details |
|--------|---------|
| **Usage** | Provision GCP Compute Engine instances |
| **Cost** | **Free** when using local backend |
| **Cloud Backend** | Optional (HCP Terraform) - $0-0.47/resource/month |
| **Version** | Use Terraform CLI locally (free) |

**Terraform Limitations:**
- Requires state management (local file or remote)
- No built-in configuration management
- HCP Terraform free tier: 500 managed resources, 1 concurrent run
- Standard tier: ~$0.10-0.47 per managed resource/month

**Recommendation:** Use Terraform CLI locally with `local` backend to avoid cloud costs entirely.

### 2.2 Ansible

**Purpose:** VM configuration and software provisioning

| Aspect | Details |
|--------|---------|
| **Usage** | Configure OS, install packages, setup tools |
| **Cost** | **Free** (using `ansible-core` CLI or AWX) |
| **AWX Cost** | Self-hosted (requires separate VM ~$5-10/mo) |
| **AAP (Enterprise)** | $5,000-14,000/year (NOT needed for this project) |

**Ansible Limitations:**
- **AWX requires its own server** to run (adds ~$5-10/mo if self-hosted)
- `ansible-core` CLI is sufficient for this use case (runs locally)
- SSH connectivity required to target machines
- Python 3.5+ required on control node
- Can be slow for one-off provisioning vs scripts

**Recommendation:** Use `ansible-core` CLI locally (free), no AWX needed. Run Ansible playbooks from controller.

---

## 3. Cloud Infrastructure

### 3.1 Provider: Google Cloud Platform (GCP)

| Option | Spec | Cost | Notes |
|--------|------|------|-------|
| **Primary** | e2-micro | **$0/mo** | Always free, 0.25 vCPU, 0.6GB RAM, 30GB HDD |
| Alt-1 | e2-small | ~$6/mo | 0.5 vCPU, 2GB RAM (recommended if budget allows) |
| Alt-2 | Custom (1 vCPU, 1GB) | ~$5/mo | DigitalOcean Droplet ($4/mo start) |

> **CRITICAL LIMITATION**: e2-micro has only 0.6GB RAM. This is severely constrained for running opencode + juggle + git + npm simultaneously. You MUST add swap (1GB minimum) or expect OOM kills.

**e2-micro constraints:**
- 0.6GB RAM - extremely tight (will cause swap thrashing)
- No swap by default (Ansible playbook adds 1GB swap)
- Must use lightweight distros and tools
- May cause intermittent failures under load

### 3.2 Operating System

**Recommendation: Alpine Linux 3.23+ (Cloud Image)**

> **RISK WARNING**: Alpine uses musl libc, not glibc. This may cause compatibility issues with opencode/juggle Python packages. Test in container first.

Reasons:
- ~130MB minimal install vs 800MB+ Ubuntu
- musl libc (smaller, more secure)
- PIE + stack smashing protection by default
- BusyBox included (minimal binaries)
- apk package manager (simple)

**Ubuntu 24 Alternative:** If Alpine compatibility issues arise
- Use minimal cloud image
- Strip down to essential packages only
- Costs ~$3/mo more but significantly more reliable

### 3.3 Security Configuration

- **Firewall:** Only allow SSH (22), block all ingress else
- **SSH:** Key-based auth only, no password
- **User:** Non-root user with sudo (if needed)
- **Updates:** apk update on boot (Alpine)
- **Network:** Private IP only (no public IP if using IAP tunnel)

---

## 4. System Components

### 4.1 Controller (Running Locally)

**Technology:** Terraform CLI + Ansible Core CLI

**Responsibilities:**

| Component | Tool | Description |
|-----------|------|-------------|
| **VM Provisioner** | Terraform | Create/destroy GCP instances |
| **Config Management** | Ansible | OS configuration, package installation |
| **State Manager** | Terrform | Track running VMs, costs, uptime |
| **Security Scanner** | Ansible | Check open ports, SSH keys, firewall |
| **Task Monitor** | Python/CLI | Poll juggle API for pending balls |
| **Auto-Shutdown** | Python/CLI | Kill VM when no balls/tasks remain |

### 4.2 Terraform Configuration

> **SECURITY**: Do NOT pass tokens via metadata_startup_script. Use Secret Manager + Ansible instead.

```hcl
# main.tf
provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_instance" "worker" {
  name         = "worker-${uuid()}"
  machine_type = var.machine_type  # Default: e2-micro
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "alpine-cloud/v20230613"
      size  = 30
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys = "${var.username}:${file(var.ssh_public_key)}"
  }
  # NOTE: No metadata_startup_script with secrets!

  labels = {
    purpose    = "agent-worker"
    managed-by = "terraform"
  }

  tags = ["worker", "ephemeral"]

  service_account {
    email  = var.service_account_email
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/compute"
    ]
  }

  # Ensure we can always destroy
  deletion_protection = false
}

# Add firewall rule to restrict SSH
resource "google_compute_firewall" "ssh_from_controller" {
  name    = "allow-ssh-from-controller"
  network = "default"
  
  source_ranges = [var.controller_ip]
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  target_tags = ["worker"]
}
```

### 4.3 Ansible Playbook

> **IMPORTANT**: This playbook fetches secrets securely from GCP Secret Manager.

```yaml
# provision.yml
---
- name: Configure Worker VM
  hosts: all
  gather_facts: yes
  become: yes
  vars:
    swap_size: "1G"  # Critical for e2-micro

  tasks:
    # CRITICAL: Add swap FIRST (e2-micro has only 0.6GB)
    - name: Create swap file
      command: |
        truncate -s {{ swap_size }} /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
      args:
        creates: /swapfile

    - name: Add swap to fstab
      lineinfile:
        path: /etc/fstab
        line: "/swapfile none swap sw 0 0"
        create: yes

    - name: Update package index
      apk:
        update_cache: yes

    - name: Install base packages
      apk:
        name:
          - git
          - python3
          - py3-pip
          - openssh-client
          - curl
          - npm
          - libc6-compat  # Required for some Python packages on Alpine
        state: present

    - name: Install gh CLI
      shell: |
        curl -fsSL https://cli.github.comarchive-keyring.gpg | dd of/packages/githubcli-=/usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        apk add --no-cache gh
      when: ansible_os_family == "Debian"

    # SECURE: Fetch token from Secret Manager, NOT from env vars or startup scripts
    - name: Fetch GitHub token from Secret Manager
      shell: |
        gcloud secrets versions access latest --secret=github-token 2>/dev/null || echo "{{ lookup('env', 'GH_TOKEN') }}"
      register: gh_token_result
      changed_when: false

    - name: Install Python packages
      pip:
        name:
          - opencode
          - juggle
        state: present

    - name: Configure git
      git_config:
        name: "{{ item.name }}"
        value: "{{ item.value }}"
        global: yes
      loop:
        - { name: "user.name", value: "Agent Worker" }
        - { name: "user.email", value: "agent@cloud" }

    - name: Clone working repository
      git:
        repo: "{{ repository_url }}"
        dest: /workspace
        version: main
        force: yes

    - name: Setup gh authentication
      shell: |
        echo {{ gh_token_result.stdout }} | gh auth login --with-token
      environment:
        GH_TOKEN: "{{ gh_token_result.stdout }}"
```

### 4.4 Tool Integration

| Tool | Purpose | Integration |
|------|---------|-------------|
| **git** | Version control | Local git commands |
| **gh** | GitHub API CLI | auth, status, push |
| **opencode** | AI coding agent | Execute on work dir |
| **juggle** | Task management | Monitor balls, update state |

### 4.5 Work Flow

```
1. Controller checks juggle for active balls
2. If balls exist and no VM running:
   a. terraform apply (provision GCP e2-micro)
   b. Wait for instance ready (SSH health check)
   c. ansible-playbook (configure VM with tools)
3. SSH into VM
4. Run work cycle:
   a. cd /workspace
   b. git pull (sync latest)
   c. opencode (process balls)
   d. juggle update (mark complete)
   e. git add . && git commit && git push
5. After work:
   a. Check juggle for more balls
   b. If none: terraform destroy
6. Log cost/metrics
```

---

## 5. Security Specification

### 5.1 Network Security

- **Firewall Rules:**
  - Ingress: TCP 22 (SSH) from controller IP only
  - Egress: Allow all (for git/npm downloads)
- **Service Account:** Minimal permissions (Compute Instance Admin, Secret Manager Reader)
- **VPC:** Default VPC with minimal subnets

### 5.2 Instance Security

- **OS:** Alpine Linux (minimal attack surface)
- **SSH:** 
  - Disable root login
  - Use project-specific SSH key
  - No password authentication
- **Secrets:** 
  - GitHub token from GCP Secret Manager or environment variable
  - Encrypted at rest

### 5.3 Controller Security

- Run from local machine (no extra VM cost)
- Service account with minimal IAM roles
- Audit logs enabled for Compute Engine

### 5.4 Required Security Mitigations

> **CRITICAL**: Implement these before first deployment.

1. **GCP Secret Manager for Tokens** (NOT env vars):
   ```hcl
   # Fetch GitHub token at runtime via Ansible, not startup script
   - name: Fetch GitHub token
     shell: |
       gcloud secrets versions access latest --secret=github-token
   ```

2. **Restrict SSH Firewall**:
   ```hcl
   resource "google_compute_firewall" "ssh_from_controller" {
     source_ranges = ["${var.controller_ip}/32"]
     allowed = [{ IPProtocol = "tcp", ports = ["22"] }]
   }
   ```

3. **Minimal Service Account**:
   ```hcl
   resource "google_service_account" "worker" {
     display_name = "Worker VM Service Account"
   }
   
   resource "google_compute_instance" "worker" {
     service_account {
       email  = google_service_account.worker.email
       scopes = ["https://www.googleapis.com/auth/devstorage.read_only"]
     }
   }
   ```

4. **Enable Budget Alerts**:
   - Set GCP billing budget at $5 threshold
   - Alert on any charges

### 5.5 Financial Safeguards

1. **Auto-shutdown**: Cron job destroys VM after N hours idle
2. **Health monitoring**: Separate process checks VM is running only when needed
3. **Tag all resources**: Enable cost breakdown by tag

---

## 6. Cost Analysis

### IaC Tools Cost

| Tool | Cost | Notes |
|------|------|-------|
| Terraform CLI | **$0** | Local backend, no cloud cost |
| Ansible Core | **$0** | CLI runs locally |
| AWX | ~$5-10/mo | Only if web UI needed (NOT required) |
| HCP Terraform | $0-0.47/resource | Optional, not needed |

### GCP e2-micro (Free Tier)

| Resource | Usage | Cost |
|----------|-------|------|
| e2-micro instance | 730 hrs/mo | $0.00 |
| Persistent Disk (30GB) | 30 GB/mo | ~$1.20/mo |
| Network egress | ~1 GB/mo | ~$0.12/mo |
| **Total** | | **~$1.32/mo** |

### Realistic Cost Scenarios

> **WARNING**: The "realistic" column assumes forgotten VMs, failed cleanups, and testing overspends.

| Scenario | Ideal | Realistic | Notes |
|----------|-------|-----------|-------|
| Single e2-micro | ~$1.32/mo | ~$3-5/mo | Budget alerts recommended |
| Single e2-small | ~$6/mo | ~$8/mo | Much more reliable |
| Forgotten VM | $0 | $1.32-6/mo | Biggest financial risk |
| Test overspend | $0 | +$10-20 | Occurs during debugging |

### Financial Safeguards (REQUIRED)

1. Set GCP budget alert at $5 threshold
2. Enable billing notifications
3. Use deletion_protection = false in Terraform
4. Implement auto-shutdown script

---

## 7. File Structure

```
cloud-worker-orchestrator/
├── terraform/
│   ├── main.tf              # VM provisioning
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   └── state.tf             # Local state config
├── ansible/
│   ├── provision.yml        # VM configuration playbook
│   ├── inventory.ini        # Inventory (dynamic)
│   ├── ansible.cfg         # Ansible config
│   └── roles/
│       └── worker/
│           └── tasks/
│               └── main.yml
├── scripts/
│   ├── run-workflow.sh      # Main orchestration script
│   └── health-check.sh      # VM readiness check
├── config/
│   ├── config.yaml          # Configuration
│   └── security-policy.json
├── requirements.txt
├── README.md
└── tests/
```

---

## 8. Key Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| **Terraform CLI (local)** | Free, no HCP Terraform needed |
| **Ansible Core (local)** | Free, no AWX needed |
| **Alpine vs Ubuntu** | 6x smaller footprint fits in 0.6GB RAM |
| **GCP e2-micro** | Free tier meets <$10/mo requirement |
| **Controller runs locally** | No extra VM cost, simpler security |
| **gh CLI over API** | Simpler auth, built-in git integration |
| **Polling vs Webhooks** | Simpler implementation for juggle |

---

## 9. Limitations Summary

### Terraform
- State management complexity with local backend
- No native drift detection without paid tiers
- HCP Terraform adds cost at scale
- Orphaned VMs if script crashes (financial risk)

### Ansible
- **No AWX**: Run `ansible-playbook` from local CLI
- SSH required to target machines
- Slower than shell scripts for simple tasks
- Python 3.5+ required on controller

### e2-micro (Critical)
- 0.6GB RAM cannot run all tools simultaneously (OOM kills)
- Requires 1GB+ swap (causes severe thrashing)
- May require sequential tool execution
- Consider e2-small if budget allows

---

## 10. Open Questions

1. **Juggle hosting:** Is juggle running locally or remotely? (affects API call)
2. **Repository:** Which repo will agents work on? (need to configure)
3. **GitHub token:** Should tokens be per-VM or shared?
4. **Multi-VM:** Need concurrent VMs or single worker sufficient?
5. **Persistence:** Store state locally or in GCP Firestore?

---

## 11. Implementation Notes

- e2-micro has limited RAM (0.6GB); consider adding swap:
  ```bash
  truncate -s 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  ```
- Test Alpine compatibility with opencode/juggle before full deployment
- Use `gcloud` CLI for simpler authentication flow
- Consider using GCP IAP for SSH (more secure than exposing port 22)

---

**Total projected cost**: ~$1.32-5/mo with budget alerts (see [risks.md](./risks.md) for financial risk analysis)

**Risk-adjusted recommendation**: Set budget alerts at $5, consider e2-small (~$6/mo) for reliability, or use Ubuntu instead of Alpine for compatibility.
